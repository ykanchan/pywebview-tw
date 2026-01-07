# S3 Remote Sync - Technical Design Document

**Project**: TiddlyWiki PyWebView Multi-Device Sync
**Version**: 1.0
**Date**: 2026-01-07
**Status**: Design Phase

---

## Executive Summary

This document outlines the technical design for adding Amazon S3-based remote synchronization to the existing local-only TiddlyWiki PyWebView application. The solution enables single-user multi-device synchronization with S3 as the persistent source of truth.

**Key Objectives**:
- Enable wiki synchronization across multiple devices via S3
- S3 as the persistent source of truth, SQLite as local backup for offline scenarios
- TiddlyWiki → S3 real-time sync (when online), with offline queueing in SQLite
- Minimize sync conflicts using Last-Write-Wins (LWW) based on tiddler modified timestamps
- Support version history and data recovery via S3 versioning

**Architecture Principles**:
- **TiddlyWiki in-memory store**: Ephemeral, active only when wiki window is open
- **SQLite + HTML**: Local persistence for offline scenarios and startup hydration
- **S3**: Persistent source of truth, accessible across all devices and future services (Lambda, etc.)

---

## Table of Contents

1. [Current Architecture Analysis](#1-current-architecture-analysis)
2. [S3 Sync Architecture](#2-s3-sync-architecture)
3. [S3 Data Structure](#3-s3-data-structure)
4. [Sync Algorithms](#4-sync-algorithms)
5. [Conflict Resolution](#5-conflict-resolution)
6. [API Specifications](#6-api-specifications)
7. [Security & Authentication](#7-security--authentication)
8. [Error Handling & Recovery](#8-error-handling--recovery)
9. [Implementation Phases](#9-implementation-phases)
10. [Testing Strategy](#10-testing-strategy)
11. [Future Enhancements](#11-future-enhancements)

---

## 1. Current Architecture Analysis

### 1.1 Existing Components

```mermaid
graph TD
    A[TiddlyWiki HTML] --> B[PyWebView Bridge]
    B --> C[WikiWindowAPI]
    C --> D[TiddlerStore SQLite]
    C --> E[WikiManager]
    E --> F[Local File System]
    
    style A fill:#e1f5ff
    style D fill:#ffe1e1
    style F fill:#e1ffe1
```

#### Core Components:
- **[`main.py`](src/main.py:1)**: Application entry point, PyWebView window management
- **[`WikiWindowAPI`](src/main.py:15)**: Per-wiki API instance exposing sync methods to TiddlyWiki
- **[`TiddlerStore`](src/api/tiddler_store.py:10)**: SQLite-based tiddler storage with JSON1 support
- **[`WikiManager`](src/api/wiki_manager.py:11)**: Wiki lifecycle management (create/delete/list)
- **[`syncadaptor.js`](plugin/src/syncadaptor.js:1)**: TiddlyWiki sync adaptor plugin

### 1.2 Current Data Flow

**Tiddler Save Flow**:
```
TiddlyWiki (user edit) 
  → syncadaptor.js (saveTiddler)
  → pywebview.api.put_tiddler(title, json)
  → WikiWindowAPI.put_tiddler()
  → TiddlerStore.put_tiddler()
  → SQLite INSERT/REPLACE
```

**Tiddler Sync Flow**:
```
TiddlyWiki (startup/poll)
  → syncadaptor.js (getUpdatedTiddlers)
  → pywebview.api.get_updated_tiddlers(since, currentTiddlers)
  → WikiWindowAPI.get_updated_tiddlers()
  → TiddlerStore.get_updated_tiddlers()
  → Returns {modifications: [], deletions: []}
```

### 1.3 Current Storage Structure

**Local File System**:
```
app/data/
├── wikis.json                           # Wiki metadata registry
└── wikis/
    ├── wiki_abc123.html                 # Full wiki HTML
    ├── wiki_abc123_tiddlers.db          # SQLite database
    └── wiki_def456.html
```

**SQLite Schema** ([`TiddlerStore._init_database`](src/api/tiddler_store.py:56)):
```sql
CREATE TABLE tiddlers (
    title TEXT PRIMARY KEY,
    tiddler_data JSON NOT NULL
);

CREATE INDEX idx_tiddler_modified 
ON tiddlers(json_extract(tiddler_data, '$.modified'));

CREATE TABLE wiki_metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
```

### 1.4 Key Observations

**Strengths**:
- ✅ Bidirectional sync already implemented (TiddlyWiki ↔ SQLite)
- ✅ Timestamp-based change tracking via `modified` field
- ✅ Efficient incremental sync using SQL indexes
- ✅ Deletion detection using current tiddler set comparison
- ✅ Smart first-sync using HTML save timestamp baseline

**Extension Points for S3 Sync**:
- 🔧 Direct TiddlyWiki → S3 sync path (real-time when online)
- 🔧 Offline operation queue in SQLite (uploads to S3 when back online)
- 🔧 S3 manifest for efficient change detection (stores tiddler modified timestamps)
- 🔧 S3 credentials storage in SQLite
- 🔧 Conflict resolution using tiddler's `modified` field (not S3 object timestamp)

**Clarified Data Flow**:
```
User Edit → TiddlyWiki (in-memory)
           ↓
           ├─→ SQLite (always, for local persistence)
           └─→ S3 (immediate if online, queued if offline)

S3 Pull → SQLite → TiddlyWiki (on startup or periodic sync)
```

---

## 2. S3 Sync Architecture

### 2.1 High-Level Architecture

```mermaid
graph TB
    subgraph "Client A - Active Wiki Window"
        A1[TiddlyWiki<br/>In-Memory]
        A2[WikiWindowAPI]
        A3[TiddlerStore<br/>SQLite]
        A4[S3SyncManager]
    end
    
    subgraph "S3 Cloud - Source of Truth"
        S1[S3 Bucket]
        S2[Versioned<br/>Tiddlers]
        S3[Manifest<br/>Metadata]
    end
    
    subgraph "Client B - Different Device"
        B1[TiddlyWiki<br/>In-Memory]
        B2[WikiWindowAPI]
        B3[TiddlerStore<br/>SQLite]
        B4[S3SyncManager]
    end
    
    A1 -->|Save| A2
    A2 -->|Store| A3
    A2 -->|Upload<br/>Real-time| A4
    A4 -->|PUT| S1
    A3 -.->|Offline Queue| A4
    
    S1 -->|Poll/Pull| B4
    B4 -->|Download| B3
    B3 -->|Load| B1
    
    S1 --> S2
    S1 --> S3
    
    style S1 fill:#ff9900
    style A1 fill:#e1f5ff
    style B1 fill:#e1f5ff
    style A3 fill:#ffe1e1
    style B3 fill:#ffe1e1
```

**Key Flow Changes**:
- **TiddlyWiki → S3**: Direct path via S3SyncManager (no SQLite intermediary)
- **SQLite role**: Local persistence + offline queue only
- **S3**: Primary storage, not a secondary sync target

### 2.2 Component Additions

#### New Components:

1. **`S3SyncManager`** (`src/api/s3_sync_manager.py`)
   - Manages all S3 operations (list, upload, download)
   - Handles compression/decompression
   - Implements sync algorithms
   - Tracks sync state

2. **`SyncCoordinator`** (`src/api/sync_coordinator.py`)
   - Background thread for periodic polling
   - Orchestrates push and pull operations
   - Manages sync queue and retry logic
   - Emits sync status events

3. **`S3Config`** (`src/api/s3_config.py`)
   - Stores S3 credentials and bucket configuration
   - Validates AWS credentials
   - Provides credential management utilities

#### Modified Components:

1. **`TiddlerStore`** (extended)
   - Add `change_source` tracking (tiddlywiki vs s3 vs initial)
   - Add sync state table
   - Track pending sync operations

2. **`WikiWindowAPI`** (extended)
   - Add `sync_to_s3()` method
   - Add `get_sync_status()` method
   - Add `configure_sync()` method

3. **React UI** (new components)
   - S3 configuration dialog
   - Sync status indicator
   - Manual sync button
   - Remote wiki browser

### 2.3 Data Flow

#### Push Flow (TiddlyWiki → S3 Real-Time):
```mermaid
sequenceDiagram
    participant TW as TiddlyWiki
    participant API as WikiWindowAPI
    participant TS as TiddlerStore
    participant SM as S3SyncManager
    participant S3 as AWS S3
    
    TW->>API: put_tiddler(title, json)
    
    par Save to SQLite (always)
        API->>TS: put_tiddler(title, json)
        Note over TS: Store locally
    and Upload to S3 (if online)
        API->>SM: upload_tiddler(title, json)
        SM->>S3: PUT tiddler/{hash}.json
        Note over S3: Store with metadata:<br/>x-amz-meta-modified=TW_timestamp
        S3-->>SM: Success + version_id
        SM->>TS: Mark as synced
    end
    
    alt Network Offline
        API->>TS: Queue for S3 upload
        Note over TS: Store in offline_queue table
    end
```

#### Pull Flow (S3 → TiddlyWiki via Manifest):
```mermaid
sequenceDiagram
    participant S3 as AWS S3
    participant SM as S3SyncManager
    participant TS as TiddlerStore
    participant TW as TiddlyWiki
    
    SM->>SM: Periodic check (30-60s)
    SM->>S3: GET manifest.json
    S3-->>SM: Manifest with tiddler timestamps
    
    SM->>SM: Compare manifest with local
    Note over SM: Identify newer tiddlers<br/>using TW modified timestamps
    
    loop For each newer tiddler
        SM->>S3: GET tiddler/{hash}.json
        S3-->>SM: Tiddler JSON
        SM->>TS: put_tiddler(title, json, source=s3)
        Note over TS: source=s3 prevents re-upload
    end
    
    Note over TW: TiddlyWiki sync adaptor<br/>detects changes via existing<br/>getUpdatedTiddlers mechanism
    TW->>API: get_updated_tiddlers()
    API->>TS: Query SQLite for changes
    TS-->>TW: Load updated tiddlers
```

**Key Change**: Use S3 manifest (not ListObjectsV2) to get tiddler modified timestamps efficiently.

---

## 3. S3 Data Structure

### 3.1 S3 Bucket Structure

```
s3://bucket-name/
└── wikis/
    ├── registry.json                          # Global wiki registry
    └── {wiki_id}/
        ├── manifest.json                      # Wiki metadata + sync state
        ├── wiki.html                          # Periodic full HTML snapshot
        └── tiddlers/
            ├── {title_sha256}.json.gz         # Compressed tiddler (versioned)
            ├── {title_sha256}.json.gz         # Another tiddler
            └── ...
```

### 3.2 Object Details

#### `registry.json` (Bucket Root)
Lists all available wikis for initial client setup.

```json
{
  "version": "1.0",
  "last_modified": "2026-01-07T21:45:00Z",
  "wikis": [
    {
      "wiki_id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "My Personal Wiki",
      "description": "Notes and knowledge base",
      "created_at": "2026-01-01T10:00:00Z",
      "last_modified": "2026-01-07T20:30:00Z",
      "tiddler_count": 142,
      "html_size_bytes": 2458361
    }
  ]
}
```

#### `manifest.json` (Per Wiki)
**Critical for Sync**: Tracks all tiddler modified timestamps for efficient change detection.

```json
{
  "version": "1.0",
  "wiki_id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "My Personal Wiki",
  "description": "Notes and knowledge base",
  "created_at": "2026-01-01T10:00:00Z",
  "last_html_save": "2026-01-07T18:00:00Z",
  "last_html_save_tw_timestamp": "20260107180000000",
  "html_version_id": "v123.abc.def",
  "tiddler_count": 142,
  "tiddlers": {
    "Getting Started": {
      "modified": "20260107180000000",
      "s3_key": "a3c5f9d2e8b1c4a7f6e3d8b2c5a9f1e4d7b3c6a8f2e5d9b4c7a1f6e3d8b2c5a9.json",
      "version_id": "v456.xyz.abc"
    },
    "My Notes": {
      "modified": "20260106120000000",
      "s3_key": "b4d6g0e3f9c2d5a8g7f4e9c3d6b0a2f5e8c4d7b9f3a6e2d9c5b8f1a4e7d0c3.json",
      "version_id": "v789.def.ghi"
    }
  }
}
```

**Purpose**:
- Single API call to get all tiddler modified timestamps
- Avoids downloading each tiddler to check if it's newer
- S3 ListObjectsV2 only returns S3 object LastModified (upload time), not tiddler modified time

#### Tiddler Object (`{title_sha256}.json`)
Individual tiddler stored as plain JSON (no compression for simplicity).

**File naming**: SHA-256 hash of tiddler title to handle special characters
```python
import hashlib
filename = hashlib.sha256(title.encode('utf-8')).hexdigest()
s3_key = f"wikis/{wiki_id}/tiddlers/{filename}.json"
```

**Content**:
```json
{
  "title": "Getting Started",
  "text": "Welcome to my wiki...",
  "tags": ["introduction", "welcome"],
  "created": "20260101100000000",
  "modified": "20260107180000000",
  "type": "text/vnd.tiddlywiki",
  "creator": "user",
  "modifier": "user"
}
```

**S3 Object Metadata** (for debugging/verification):
- `x-amz-meta-title`: Original tiddler title
- `x-amz-meta-modified`: TiddlyWiki timestamp (same as in JSON)
- `Content-Type`: `application/json`

**Note**: No compression - tiddlers are typically small (<10KB), simplicity preferred over bandwidth savings.

### 3.3 Naming Conventions

| Resource | Pattern | Example |
|----------|---------|---------|
| Registry | `registry.json` | `registry.json` |
| Wiki Manifest | `wikis/{wiki_id}/manifest.json` | `wikis/550e8400.../manifest.json` |
| HTML Snapshot | `wikis/{wiki_id}/wiki.html` | `wikis/550e8400.../wiki.html` |
| Tiddler Object | `wikis/{wiki_id}/tiddlers/{sha256}.json` | `wikis/550e8400.../tiddlers/a3c5f9...json` |

### 3.4 S3 Bucket Configuration

**Recommended Settings**:
- ✅ **Versioning**: Enabled (for history and recovery)
- ✅ **Encryption**: SSE-S3 (default S3 encryption)
- ✅ **Lifecycle Policy**: Archive old versions to Glacier after 90 days
- ✅ **CORS**: Disabled (not needed for server-side access)
- ✅ **Public Access**: Blocked (private bucket)

---

## 4. Sync Algorithms

### 4.1 Sync Operation Types

#### 4.1.1 Push Operation (TiddlyWiki → S3 Real-Time)

**Trigger Conditions**:
- **Immediate**: Every tiddler save from TiddlyWiki (real-time)
- **Batch upload**: Process offline queue when network restored

**Algorithm** (Called from WikiWindowAPI.put_tiddler):
```python
def upload_tiddler_to_s3(wiki_id, title, tiddler_json):
    """Upload single tiddler to S3 immediately after TiddlyWiki save"""
    
    try:
        # 1. Parse tiddler to get modified timestamp
        tiddler_data = json.loads(tiddler_json)
        tiddler_modified = tiddler_data.get('modified')
        
        # 2. Download current manifest to check for conflicts
        manifest = download_s3_manifest(wiki_id)
        
        # 3. Check if S3 has newer version (conflict detection)
        if title in manifest.get('tiddlers', {}):
            s3_modified = manifest['tiddlers'][title]['modified']
            
            if s3_modified > tiddler_modified:
                # S3 has newer version - conflict!
                # Log conflict, use LWW (S3 wins)
                log_conflict(wiki_id, title, tiddler_modified, s3_modified)
                return {"status": "conflict", "resolution": "s3_newer"}
        
        # 4. Upload to S3 (no compression)
        title_hash = hashlib.sha256(title.encode('utf-8')).hexdigest()
        s3_key = f"wikis/{wiki_id}/tiddlers/{title_hash}.json"
        
        response = s3_client.put_object(
            Key=s3_key,
            Body=tiddler_json.encode('utf-8'),
            ContentType='application/json',
            Metadata={
                'title': title,
                'modified': tiddler_modified
            }
        )
        
        version_id = response['VersionId']
        
        # 5. Update manifest with new tiddler entry
        manifest['tiddlers'][title] = {
            'modified': tiddler_modified,
            's3_key': f"{title_hash}.json",
            'version_id': version_id
        }
        manifest['tiddler_count'] = len(manifest['tiddlers'])
        
        upload_s3_manifest(wiki_id, manifest)
        
        return {
            "status": "success",
            "version_id": version_id
        }
        
    except (NetworkError, S3Error) as e:
        # Network failure - queue for later upload
        queue_for_offline_upload(wiki_id, title, tiddler_json)
        return {"status": "queued", "error": str(e)}
```

**Offline Queue Processing**:
```python
def process_offline_queue(wiki_id):
    """Process queued uploads when network is restored"""
    
    queued_tiddlers = get_offline_queue(wiki_id)
    
    for title, tiddler_json in queued_tiddlers:
        result = upload_tiddler_to_s3(wiki_id, title, tiddler_json)
        
        if result['status'] == 'success':
            remove_from_queue(wiki_id, title)
```

#### 4.1.2 Pull Operation (S3 → SQLite via Manifest)

**Trigger Conditions**:
- Periodic timer (default: 30-60 seconds for manifest check)
- Manual sync button clicked
- App startup

**Algorithm**:
```python
def pull_from_s3(wiki_id):
    """Pull remote changes from S3 using manifest for efficiency"""
    
    # 1. Download current S3 manifest
    s3_manifest = download_s3_manifest(wiki_id)
    
    # 2. Get local manifest state (last known S3 state)
    local_manifest_cache = get_local_manifest_cache(wiki_id)
    
    # 3. Compare manifests to find changed tiddlers
    # Compare tiddler modified timestamps (not S3 object timestamps)
    changed_tiddlers = []
    
    for title, s3_meta in s3_manifest.get('tiddlers', {}).items():
        s3_modified = s3_meta['modified']
        
        # Check if we have this tiddler locally
        local_tiddler = tiddler_store.get_tiddler(title)
        
        if not local_tiddler:
            # New tiddler, download it
            changed_tiddlers.append(title)
        else:
            local_modified = json.loads(local_tiddler).get('modified')
            
            if s3_modified > local_modified:
                # S3 version is newer, download it
                changed_tiddlers.append(title)
    
    # 4. Detect deletions (tiddlers in local but not in S3 manifest)
    local_titles = set(get_all_local_tiddler_titles(wiki_id))
    s3_titles = set(s3_manifest.get('tiddlers', {}).keys())
    deleted_titles = local_titles - s3_titles
    
    if not changed_tiddlers and not deleted_titles:
        return {"status": "no_changes"}
    
    # 5. Download changed tiddlers
    downloaded = []
    
    for title in changed_tiddlers:
        s3_key = f"wikis/{wiki_id}/tiddlers/{s3_manifest['tiddlers'][title]['s3_key']}"
        
        obj_data = s3_client.get_object(
            Bucket=bucket_name,
            Key=s3_key
        )
        
        tiddler_json = obj_data['Body'].read().decode('utf-8')
        
        # Store in local SQLite with source=s3 (prevents re-upload)
        tiddler_store.put_tiddler(
            title=title,
            tiddler_json=tiddler_json,
            source='s3'
        )
        
        downloaded.append(title)
    
    # 6. Handle deletions
    for title in deleted_titles:
        tiddler_store.delete_tiddler(title)
    
    # 7. Update local manifest cache
    save_local_manifest_cache(wiki_id, s3_manifest)
    
    return {
        "status": "success",
        "downloaded": downloaded,
        "deleted": list(deleted_titles)
    }
```

**Key Efficiency**:
- Single manifest download reveals all changes
- Only download tiddlers that actually changed
- No need to list or download all S3 objects

#### 4.1.3 Offline Queue Management

**Process queued uploads when network restored**:

```python
def process_offline_queue_batch(wiki_id):
    """Batch process offline queue"""
    
    # 1. Check network connectivity
    if not check_s3_connectivity():
        return {"status": "offline"}
    
    # 2. Get all queued tiddlers
    queued_items = tiddler_store.get_offline_queue(wiki_id)
    
    if not queued_items:
        return {"status": "queue_empty"}
    
    # 3. Upload each queued tiddler
    uploaded = []
    failed = []
    
    for title, tiddler_json, queued_at in queued_items:
        try:
            result = upload_tiddler_to_s3(wiki_id, title, tiddler_json)
            
            if result['status'] == 'success':
                tiddler_store.remove_from_offline_queue(wiki_id, title)
                uploaded.append(title)
            else:
                failed.append({'title': title, 'error': result.get('error')})
                
        except Exception as e:
            failed.append({'title': title, 'error': str(e)})
    
    return {
        "status": "completed",
        "uploaded": uploaded,
        "failed": failed
    }
```

### 4.2 Initial Sync (New Client Setup)

**Scenario**: User sets up application on a new device with existing S3 wikis.

```python
def initial_sync_from_s3(wiki_id):
    """Download wiki from S3 for first time"""
    
    # 1. Download registry to list available wikis
    registry = download_s3_registry()
    
    # 2. User selects wiki to sync
    wiki_info = registry['wikis'].find(id=wiki_id)
    
    # 3. Download wiki HTML file (contains bulk tiddlers)
    html_response = s3_client.get_object(
        Key=f"wikis/{wiki_id}/wiki.html"
    )
    html_data = html_response['Body'].read()
    
    # 4. Save HTML locally
    local_wiki_path = save_wiki_html(wiki_id, html_data)
    
    # 5. Download manifest
    manifest_response = s3_client.get_object(
        Key=f"wikis/{wiki_id}/manifest.json"
    )
    manifest = json.loads(manifest_response['Body'].read())
    
    html_save_timestamp = manifest['last_html_save_tw_timestamp']
    
    # 6. Download only tiddlers modified AFTER the HTML save
    # (HTML already contains older tiddlers)
    incremental_tiddlers = []
    
    for title, meta in manifest.get('tiddlers', {}).items():
        if meta['modified'] > html_save_timestamp:
            incremental_tiddlers.append({
                'title': title,
                's3_key': f"wikis/{wiki_id}/tiddlers/{meta['s3_key']}"
            })
    
    # 7. Download and store incremental tiddlers
    for tiddler_info in incremental_tiddlers:
        obj_data = s3_client.get_object(
            Bucket=bucket_name,
            Key=tiddler_info['s3_key']
        )
        tiddler_json = obj_data['Body'].read().decode('utf-8')
        
        tiddler_store.put_tiddler(
            title=tiddler_info['title'],
            tiddler_json=tiddler_json,
            source='initial'
        )
    
    # 8. Initialize sync state and cache manifest
    save_local_manifest_cache(wiki_id, manifest)
    
    return {
        "status": "success",
        "wiki_id": wiki_id,
        "tiddlers_from_html": "embedded",
        "incremental_tiddlers": len(incremental_tiddlers)
    }
```

### 4.3 HTML Snapshot Upload

**Trigger**: Periodic (e.g., daily) or manual

```python
def upload_html_snapshot(wiki_id):
    """Upload full HTML snapshot to S3"""
    
    # 1. Get local HTML file
    wiki_path = wiki_manager.get_wiki_path(wiki_id)
    
    with open(wiki_path, 'rb') as f:
        html_data = f.read()
    
    # 2. Upload to S3
    response = s3_client.put_object(
        Key=f"wikis/{wiki_id}/wiki.html",
        Body=html_data,
        ContentType='text/html',
        Metadata={
            'snapshot_timestamp': now_iso(),
            'tiddler_count': str(get_local_tiddler_count(wiki_id))
        }
    )
    
    version_id = response['VersionId']
    
    # 3. Update manifest
    manifest = download_s3_manifest(wiki_id)
    manifest['last_html_save'] = now_iso()
    manifest['last_html_save_tw_timestamp'] = now_tiddlywiki()
    manifest['html_version_id'] = version_id
    
    upload_s3_manifest(wiki_id, manifest)
    
    # 4. Record in local metadata
    tiddler_store.record_html_save()
    
    return {
        "status": "success",
        "version_id": version_id,
        "size_bytes": len(html_data)
    }
```

### 4.4 Manifest Update Strategy (Race Condition Prevention)

**Problem**: Multiple clients uploading tiddlers simultaneously could overwrite each other's manifest updates.

**Solution**: Use S3 conditional writes with ETag matching to ensure atomic manifest updates.

#### ETag-Based Conditional Write

**How S3 ETags Work**:
- Every S3 object has an ETag (entity tag) that changes when the object is modified
- Use `If-Match` header to only update if ETag matches expected value
- If ETag doesn't match, S3 returns 412 Precondition Failed

**Implementation**:

```python
def update_manifest_atomic(wiki_id, update_function, max_retries=3):
    """
    Atomically update manifest with retry on conflict.
    
    Args:
        wiki_id: Wiki UUID
        update_function: Function that takes manifest dict and modifies it
        max_retries: Maximum retry attempts on ETag mismatch
    
    Returns:
        Updated manifest dict
    """
    
    for attempt in range(max_retries):
        try:
            # 1. Download current manifest with ETag
            manifest_key = f"wikis/{wiki_id}/manifest.json"
            
            response = s3_client.get_object(
                Bucket=bucket_name,
                Key=manifest_key
            )
            
            current_manifest = json.loads(response['Body'].read())
            current_etag = response['ETag'].strip('"')  # Remove quotes
            
            # 2. Apply user's update function
            updated_manifest = update_function(current_manifest)
            
            # 3. Upload with If-Match condition (only if ETag unchanged)
            manifest_json = json.dumps(updated_manifest, indent=2)
            
            upload_response = s3_client.put_object(
                Bucket=bucket_name,
                Key=manifest_key,
                Body=manifest_json.encode('utf-8'),
                ContentType='application/json',
                Metadata={
                    'updated_at': datetime.utcnow().isoformat() + 'Z'
                },
                # CRITICAL: Only update if ETag matches (no concurrent modification)
                IfMatch=current_etag
            )
            
            # Success!
            return updated_manifest
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            
            if error_code == 'PreconditionFailed':
                # Another client modified manifest - retry
                if attempt < max_retries - 1:
                    print(f"Manifest conflict detected, retry {attempt + 1}/{max_retries}")
                    time.sleep(0.1 * (2 ** attempt))  # Exponential backoff
                    continue
                else:
                    raise Exception("Manifest update failed after max retries (concurrent modification)")
            else:
                # Other error
                raise
```

#### Usage in Tiddler Upload

**Updated upload_tiddler_to_s3 with atomic manifest update**:

```python
def upload_tiddler_to_s3(wiki_id, title, tiddler_json):
    """Upload tiddler with atomic manifest update"""
    
    # 1. Parse tiddler data
    tiddler_data = json.loads(tiddler_json)
    tiddler_modified = tiddler_data.get('modified')
    
    # 2. Upload tiddler to S3
    title_hash = hashlib.sha256(title.encode('utf-8')).hexdigest()
    s3_key = f"wikis/{wiki_id}/tiddlers/{title_hash}.json"
    
    tiddler_response = s3_client.put_object(
        Key=s3_key,
        Body=tiddler_json.encode('utf-8'),
        ContentType='application/json',
        Metadata={
            'title': title,
            'modified': tiddler_modified
        }
    )
    
    version_id = tiddler_response['VersionId']
    
    # 3. Update manifest atomically using ETag-based conditional write
    def add_tiddler_to_manifest(manifest):
        """Update function: adds/updates tiddler entry"""
        if 'tiddlers' not in manifest:
            manifest['tiddlers'] = {}
        
        manifest['tiddlers'][title] = {
            'modified': tiddler_modified,
            's3_key': f"{title_hash}.json",
            'version_id': version_id
        }
        manifest['tiddler_count'] = len(manifest['tiddlers'])
        manifest['last_modified'] = datetime.utcnow().isoformat() + 'Z'
        
        return manifest
    
    # This will retry automatically if another client updated manifest concurrently
    updated_manifest = update_manifest_atomic(wiki_id, add_tiddler_to_manifest)
    
    return {
        "status": "success",
        "version_id": version_id
    }
```

#### Benefits of ETag-Based Approach

1. **Prevents Lost Updates**: If Client A and Client B both upload tiddlers simultaneously:
   - Client A downloads manifest (ETag: "abc123")
   - Client B downloads manifest (ETag: "abc123")
   - Client A uploads tiddler, updates manifest (new ETag: "def456")
   - Client B tries to upload with If-Match: "abc123" → **Fails with 412**
   - Client B retries: downloads fresh manifest (ETag: "def456"), merges changes, succeeds

2. **Automatic Retry**: The `update_manifest_atomic` function handles retries transparently

3. **No Data Loss**: All tiddler uploads are preserved, even with concurrent modifications

4. **Minimal Performance Impact**: Retries only needed when actual conflicts occur (rare in single-user scenario)

#### Edge Case: Initial Manifest Creation

If manifest doesn't exist yet (first wiki setup):

```python
def create_initial_manifest(wiki_id, wiki_name, description):
    """Create initial manifest for new wiki"""
    
    manifest = {
        "version": "1.0",
        "wiki_id": wiki_id,
        "name": wiki_name,
        "description": description,
        "created_at": datetime.utcnow().isoformat() + 'Z',
        "last_html_save": None,
        "last_html_save_tw_timestamp": None,
        "html_version_id": None,
        "tiddler_count": 0,
        "tiddlers": {}
    }
    
    manifest_json = json.dumps(manifest, indent=2)
    
    # Use IfNoneMatch='*' to only create if doesn't exist
    try:
        s3_client.put_object(
            Bucket=bucket_name,
            Key=f"wikis/{wiki_id}/manifest.json",
            Body=manifest_json.encode('utf-8'),
            ContentType='application/json',
            IfNoneMatch='*'  # Only create if doesn't exist
        )
    except ClientError as e:
        if e.response['Error']['Code'] == 'PreconditionFailed':
            # Manifest already exists (another client created it)
            pass
        else:
            raise
    
    return manifest
```

---

## 5. Conflict Resolution

### 5.1 Last-Write-Wins Strategy

**Core Principle**: Use TiddlyWiki's `modified` timestamp field to determine latest version.

**Implementation**:
```python
def resolve_conflict_lww(local_tiddler, s3_tiddler):
    """
    Resolve conflict using Last-Write-Wins based on modified timestamp.
    
    Returns: ('local', 's3', or 'equal')
    """
    local_modified = local_tiddler.get('modified', '00000000000000000')
    s3_modified = s3_tiddler.get('modified', '00000000000000000')
    
    if local_modified > s3_modified:
        return 'local'
    elif s3_modified > local_modified:
        return 's3'
    else:
        # Timestamps equal - compare content hash as tiebreaker
        local_hash = hash_tiddler_content(local_tiddler)
        s3_hash = hash_tiddler_content(s3_tiddler)
        
        if local_hash == s3_hash:
            return 'equal'  # Identical content
        else:
            # Same timestamp, different content - rare edge case
            # Fall back to S3 (remote) as source of truth
            return 's3'
```

### 5.2 Sync Loop Prevention

**Problem**: Prevent S3→SQLite updates from triggering SQLite→S3 uploads (sync loop).

**Solution**: Track change source and only upload TiddlyWiki-originated changes.

**Extended TiddlerStore Schema**:
```sql
CREATE TABLE tiddlers (
    title TEXT PRIMARY KEY,
    tiddler_data JSON NOT NULL,
    change_source TEXT NOT NULL DEFAULT 'tiddlywiki',  -- 'tiddlywiki', 's3', 'initial'
    last_synced_to_s3 TEXT,                            -- TW timestamp when last uploaded
    CHECK (change_source IN ('tiddlywiki', 's3', 'initial'))
);

CREATE TABLE offline_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    wiki_id TEXT NOT NULL,
    title TEXT NOT NULL,
    tiddler_json TEXT NOT NULL,
    queued_at TEXT NOT NULL,
    retry_count INTEGER DEFAULT 0,
    UNIQUE(wiki_id, title)
);
```

**Logic in WikiWindowAPI.put_tiddler**:
```python
def put_tiddler(self, title: str, tiddler_json: str) -> dict:
    """
    Called by TiddlyWiki when user saves a tiddler.
    Immediately uploads to S3 and saves to SQLite.
    """
    # 1. Save to SQLite (always, for local persistence)
    self._tiddler_store.put_tiddler(
        title=title,
        tiddler_json=tiddler_json,
        source='tiddlywiki'  # Mark as TiddlyWiki-originated
    )
    
    # 2. Upload to S3 immediately (real-time sync)
    if self._s3_sync_enabled:
        try:
            result = self._s3_sync_manager.upload_tiddler_to_s3(
                wiki_id=self.wiki_id,
                title=title,
                tiddler_json=tiddler_json
            )
            
            if result['status'] == 'success':
                # Mark as synced
                self._tiddler_store.mark_synced_to_s3(title)
            elif result['status'] == 'queued':
                # Network failure - already queued by upload_tiddler_to_s3
                pass
                
        except Exception as e:
            # Queue for offline upload
            self._tiddler_store.add_to_offline_queue(
                wiki_id=self.wiki_id,
                title=title,
                tiddler_json=tiddler_json
            )
    
    return {"success": True}
```

**Pull from S3 with source tracking**:
```python
# When pulling from S3, mark source='s3' to prevent re-upload
tiddler_store.put_tiddler(
    title=title,
    tiddler_json=tiddler_json,
    source='s3'  # Prevents triggering S3 upload
)
```

### 5.3 Timestamp Source Clarification

**Critical**: Use tiddler's `modified` field for conflict resolution, NOT S3 object's LastModified.

**Why**:
- S3 object LastModified = when uploaded to S3
- Tiddler modified field = when edited in TiddlyWiki
- These can differ significantly (offline edits, batch uploads, etc.)

**Implementation**:
```python
def resolve_conflict_lww(local_tiddler_json, s3_tiddler_json):
    """
    Resolve conflict using tiddler's modified timestamp (not S3 upload time).
    
    Returns: 'local' or 's3'
    """
    local_data = json.loads(local_tiddler_json)
    s3_data = json.loads(s3_tiddler_json)
    
    # Compare TiddlyWiki modified timestamps (format: YYYYMMDDHHMMSSmmm)
    local_modified = local_data.get('modified', '00000000000000000')
    s3_modified = s3_data.get('modified', '00000000000000000')
    
    if s3_modified > local_modified:
        return 's3'
    else:
        return 'local'  # Local wins on tie
```

**Efficient Access via Manifest**:
- S3 ListObjectsV2 only returns S3 object timestamps (not tiddler timestamps)
- Solution: Store tiddler modified timestamps in manifest.json
- Single manifest download gives all tiddler timestamps
- No need to download each tiddler just to check its timestamp

---

## 6. API Specifications

### 6.1 Python Backend API

#### S3SyncManager Class

```python
class S3SyncManager:
    """Manages S3 synchronization for a specific wiki"""
    
    def __init__(self, wiki_id: str, s3_config: S3Config):
        """Initialize S3 sync manager for a specific wiki"""
        pass
    
    def upload_tiddler_to_s3(self, wiki_id: str, title: str, tiddler_json: str) -> dict:
        """Upload single tiddler to S3 immediately (real-time sync)
        
        Called by WikiWindowAPI.put_tiddler after every TiddlyWiki save.
        
        Returns:
            {
                "status": "success" | "queued" | "conflict",
                "version_id": str | None,
                "error": str | None
            }
        """
        pass
    
    def pull_from_s3(self) -> dict:
        """Pull remote changes from S3 using manifest
        
        Returns:
            {
                "status": "success" | "error",
                "downloaded": [tiddler_titles],
                "deleted": [tiddler_titles],
                "error": str | None
            }
        """
        pass
    
    def process_offline_queue(self, wiki_id: str) -> dict:
        """Process offline queue when network restored"""
        pass
    
    def upload_html_snapshot(self) -> dict:
        """Upload full HTML snapshot to S3 (periodic)"""
        pass
    
    def download_wiki_from_s3(self, wiki_id: str) -> dict:
        """Initial download of wiki from S3 (new client setup)"""
        pass
    
    def download_manifest(self, wiki_id: str) -> dict:
        """Download manifest.json from S3"""
        pass
    
    def upload_manifest(self, wiki_id: str, manifest: dict) -> dict:
        """Upload updated manifest.json to S3"""
        pass
    
    @staticmethod
    def list_remote_wikis(s3_config: S3Config) -> list:
        """List all wikis available in S3 (static method, no wiki_id needed)
        
        Returns:
            [
                {
                    "wiki_id": str,
                    "name": str,
                    "description": str,
                    "last_modified": str,
                    "tiddler_count": int
                }
            ]
        """
        pass
    
    def get_sync_status(self) -> dict:
        """Get current sync status for this wiki
        
        Returns:
            {
                "last_pull": str (ISO timestamp),
                "offline_queue_count": int,
                "is_pulling": bool,
                "sync_enabled": bool
            }
        """
        pass
```

#### WikiWindowAPI Extensions

**Note**: S3 sync is transparent to individual wiki windows. The WikiWindowAPI just uploads to S3 immediately on each save.

```python
class WikiWindowAPI:
    # ... existing methods ...
    
    def __init__(self, wiki_id: str, wiki_path: str, wiki_manager: WikiManager):
        # ... existing initialization ...
        
        # Initialize S3 sync manager if configured
        s3_config = load_s3_config()  # From SQLite
        if s3_config and s3_config.enabled:
            self._s3_sync_manager = S3SyncManager(wiki_id, s3_config)
            self._s3_sync_enabled = True
            
            # Start background pull thread for this wiki
            self._sync_coordinator = SyncCoordinator(
                wiki_id=wiki_id,
                s3_sync_manager=self._s3_sync_manager,
                interval_seconds=60  # Check S3 every 60 seconds
            )
            self._sync_coordinator.start()
        else:
            self._s3_sync_enabled = False
    
    def put_tiddler(self, title: str, tiddler_json: str) -> dict:
        """Modified to include real-time S3 upload"""
        # Save to SQLite
        self._tiddler_store.put_tiddler(title, tiddler_json, source='tiddlywiki')
        
        # Upload to S3 immediately (if enabled)
        if self._s3_sync_enabled:
            try:
                self._s3_sync_manager.upload_tiddler_to_s3(
                    self.wiki_id, title, tiddler_json
                )
            except Exception as e:
                # Offline - already queued
                print(f"S3 upload failed, queued: {e}")
        
        return {"success": True}
    
    def get_sync_status(self) -> dict:
        """Get S3 sync status for this wiki"""
        if not self._s3_sync_enabled:
            return {"sync_enabled": False}
        
        return self._s3_sync_manager.get_sync_status()
```

### 6.2 TiddlyWiki Plugin Changes

**No S3-specific changes needed**. TiddlyWiki remains unaware of S3.

The existing [`syncadaptor.js`](plugin/src/syncadaptor.js:1) already handles:
- `saveTiddler()` → calls `pywebview.api.put_tiddler()` → WikiWindowAPI handles S3 upload
- `loadTiddler()` → calls `pywebview.api.get_tiddler()` → loads from SQLite (populated by S3 pull)
- `getUpdatedTiddlers()` → calls `pywebview.api.get_updated_tiddlers()` → SQLite returns S3-pulled changes

**S3 sync is completely transparent to TiddlyWiki.**

### 6.3 React UI API

**Limited scope**: React app only handles S3 configuration, not individual wiki sync.

```typescript
// API calls from React frontend (MultiWikiApp exposed methods)
interface WikiAPI {
    // Existing methods...
    
    // S3 Configuration only (global, not per-wiki)
    configureS3(config: S3Config): Promise<void>;
    getS3Config(): Promise<S3Config | null>;
    listRemoteWikis(): Promise<WikiInfo[]>;
    downloadRemoteWiki(wikiId: string): Promise<WikiDownloadResult>;
}

interface S3Config {
    bucketName: string;
    region: string;
    accessKeyId: string;
    secretAccessKey: string;
    enabled: boolean;
}

interface WikiDownloadResult {
    status: 'success' | 'error';
    wikiId: string;
    wikiName: string;
    error?: string;
}
```

**Key principle**: Each wiki window manages its own sync independently via WikiWindowAPI. React app doesn't track or control per-wiki sync status.

---

## 7. Security & Authentication

### 7.1 AWS Credentials Storage

**Single Option**: Store in SQLite database (simple, cross-platform).

**SQLite Schema for S3 Config**:
```sql
CREATE TABLE s3_config (
    id INTEGER PRIMARY KEY CHECK (id = 1),  -- Only one row allowed
    bucket_name TEXT NOT NULL,
    region TEXT NOT NULL DEFAULT 'us-east-1',
    access_key_id TEXT NOT NULL,
    secret_access_key TEXT NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
```

**Location**: Store in global metadata DB or wiki-manager level DB (shared across all wikis).

**Implementation**:
```python
class S3Config:
    """Manages S3 configuration stored in SQLite"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_config_table()
    
    def _init_config_table(self):
        """Create S3 config table if not exists"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS s3_config (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                bucket_name TEXT NOT NULL,
                region TEXT NOT NULL DEFAULT 'us-east-1',
                access_key_id TEXT NOT NULL,
                secret_access_key TEXT NOT NULL,
                enabled BOOLEAN NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        conn.commit()
        conn.close()
    
    def save_config(self, bucket_name: str, region: str,
                   access_key_id: str, secret_access_key: str, enabled: bool = True):
        """Save S3 configuration"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        now = datetime.utcnow().isoformat() + 'Z'
        
        cursor.execute("""
            INSERT OR REPLACE INTO s3_config
            (id, bucket_name, region, access_key_id, secret_access_key, enabled, created_at, updated_at)
            VALUES (1, ?, ?, ?, ?, ?, COALESCE((SELECT created_at FROM s3_config WHERE id=1), ?), ?)
        """, (bucket_name, region, access_key_id, secret_access_key, enabled, now, now))
        
        conn.commit()
        conn.close()
    
    def load_config(self) -> dict | None:
        """Load S3 configuration"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM s3_config WHERE id = 1")
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        return {
            'bucket_name': row[1],
            'region': row[2],
            'access_key_id': row[3],
            'secret_access_key': row[4],
            'enabled': bool(row[5])
        }
```

**Note**: Credentials stored in plaintext in SQLite. For production, consider encryption (future enhancement).

### 7.2 S3 Bucket Permissions

**Recommended IAM Policy**:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:ListBucket",
        "s3:GetBucketVersioning"
      ],
      "Resource": "arn:aws:s3:::my-wiki-bucket"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:GetObjectVersion",
        "s3:PutObject",
        "s3:DeleteObject"
      ],
      "Resource": "arn:aws:s3:::my-wiki-bucket/wikis/*"
    }
  ]
}
```

**Security Best Practices**:
- ✅ Use IAM user with minimal permissions (not root account)
- ✅ Enable MFA for IAM user
- ✅ Rotate access keys regularly
- ✅ Use S3 bucket policies to restrict access by IP (optional)
- ✅ Enable S3 access logging
- ✅ Never commit credentials to version control

### 7.3 Data Encryption

**At Rest**:
- S3 Server-Side Encryption (SSE-S3) enabled by default
- Alternative: SSE-KMS for customer-managed keys

**In Transit**:
- All S3 API calls use HTTPS (boto3 default)
- TLS 1.2+ enforced

**Local Storage**:
- Credentials encrypted using platform keyring (Keychain on macOS, Credential Manager on Windows)
- SQLite database can be encrypted using SQLCipher (future enhancement)

---

## 8. Error Handling & Recovery

### 8.1 Network Failures

**Retry Strategy**:
```python
import time
from botocore.exceptions import ClientError

def upload_with_retry(s3_client, key, data, max_retries=3):
    """Upload to S3 with exponential backoff retry"""
    
    for attempt in range(max_retries):
        try:
            response = s3_client.put_object(
                Key=key,
                Body=data
            )
            return response
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            
            if error_code in ['RequestTimeout', 'ServiceUnavailable']:
                # Retryable errors
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                    time.sleep(wait_time)
                    continue
                else:
                    raise
            else:
                # Non-retryable error
                raise
```

### 8.2 Offline Operation

**Queue Pending Operations**:
```python
class SyncQueue:
    """Queue for offline sync operations"""
    
    def __init__(self, db_path):
        self.conn = sqlite3.connect(db_path)
        self._init_queue_table()
    
    def _init_queue_table(self):
        """Create queue table for pending operations"""
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS sync_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                wiki_id TEXT NOT NULL,
                operation TEXT NOT NULL,  -- 'upload' or 'download'
                tiddler_title TEXT NOT NULL,
                created_at TEXT NOT NULL,
                retry_count INTEGER DEFAULT 0,
                last_error TEXT
            )
        """)
    
    def enqueue(self, wiki_id, operation, tiddler_title):
        """Add operation to queue"""
        self.conn.execute("""
            INSERT INTO sync_queue (wiki_id, operation, tiddler_title, created_at)
            VALUES (?, ?, ?, ?)
        """, (wiki_id, operation, tiddler_title, datetime.utcnow().isoformat()))
        self.conn.commit()
    
    def process_queue(self):
        """Process all queued operations"""
        cursor = self.conn.execute("""
            SELECT id, wiki_id, operation, tiddler_title
            FROM sync_queue
            WHERE retry_count < 5
            ORDER BY created_at
        """)
        
        for row in cursor:
            try:
                if row[2] == 'upload':
                    upload_tiddler(row[1], row[3])
                else:
                    download_tiddler(row[1], row[3])
                
                # Remove from queue on success
                self.conn.execute("DELETE FROM sync_queue WHERE id = ?", (row[0],))
                self.conn.commit()
                
            except Exception as e:
                # Increment retry count and record error
                self.conn.execute("""
                    UPDATE sync_queue 
                    SET retry_count = retry_count + 1,
                        last_error = ?
                    WHERE id = ?
                """, (str(e), row[0]))
                self.conn.commit()
```

### 8.3 Corruption Detection

**Checksum Validation**:
```python
def upload_tiddler_with_checksum(s3_client, key, tiddler_data):
    """Upload tiddler with checksum validation"""
    
    # Calculate MD5 checksum
    import hashlib
    md5_hash = hashlib.md5(tiddler_data).digest()
    md5_base64 = base64.b64encode(md5_hash).decode()
    
    # Upload with checksum
    response = s3_client.put_object(
        Key=key,
        Body=tiddler_data,
        ContentMD5=md5_base64  # S3 will verify this
    )
    
    # Verify ETag matches
    etag = response['ETag'].strip('"')
    expected_etag = md5_hash.hex()
    
    if etag != expected_etag:
        raise ValueError(f"Checksum mismatch: {etag} != {expected_etag}")
    
    return response
```

### 8.4 Version Conflict Recovery

**Browse S3 Version History**:
```python
def list_tiddler_versions(wiki_id, tiddler_title):
    """List all versions of a tiddler in S3"""
    
    title_hash = hashlib.sha256(tiddler_title.encode('utf-8')).hexdigest()
    key = f"wikis/{wiki_id}/tiddlers/{title_hash}.json.gz"
    
    response = s3_client.list_object_versions(
        Bucket=bucket_name,
        Prefix=key
    )
    
    versions = []
    for version in response.get('Versions', []):
        versions.append({
            'version_id': version['VersionId'],
            'last_modified': version['LastModified'].isoformat(),
            'size': version['Size'],
            'is_latest': version['IsLatest']
        })
    
    return versions

def restore_tiddler_version(wiki_id, tiddler_title, version_id):
    """Restore a specific version of a tiddler"""
    
    title_hash = hashlib.sha256(tiddler_title.encode('utf-8')).hexdigest()
    key = f"wikis/{wiki_id}/tiddlers/{title_hash}.json.gz"
    
    # Download specific version
    response = s3_client.get_object(
        Bucket=bucket_name,
        Key=key,
        VersionId=version_id
    )
    
    tiddler_data = response['Body'].read()
    
    # Re-upload as current version
    s3_client.put_object(
        Key=key,
        Body=tiddler_data
    )
```

---

## 9. Implementation Phases

### Phase 1: Foundation (MVP)
**Goal**: Basic S3 sync with manual trigger

**Components**:
- ✅ S3SyncManager class
- ✅ S3Config credential management
- ✅ Extended TiddlerStore with change_source tracking
- ✅ Basic push/pull algorithms (no conflict detection)
- ✅ Manual sync button in UI

**Deliverables**:
1. `src/api/s3_sync_manager.py` - Core sync logic
2. `src/api/s3_config.py` - Credential management
3. Modified `src/api/tiddler_store.py` - Add change_source column
4. Modified `src/main.py` - Add sync API methods
5. React component: S3ConfigDialog
6. React component: SyncButton

**Testing**:
- Unit tests for S3SyncManager
- Integration test: push local changes to S3
- Integration test: pull remote changes from S3
- End-to-end: sync between two clients

**Estimated Effort**: 2-3 weeks

---

### Phase 2: Automation & Reliability
**Goal**: Automatic sync with offline support

**Components**:
- ✅ SyncCoordinator background thread
- ✅ Periodic polling (configurable interval)
- ✅ Offline queue for failed operations
- ✅ Retry logic with exponential backoff
- ✅ Conflict detection and LWW resolution
- ✅ Sync status indicator in UI

**Deliverables**:
1. `src/api/sync_coordinator.py` - Background sync thread
2. `src/api/sync_queue.py` - Offline operation queue
3. Extended TiddlerStore - Sync queue table
4. React component: SyncStatusIndicator
5. Notification system for sync events

**Testing**:
- Test periodic sync triggers
- Test offline queue processing
- Test conflict resolution (LWW)
- Load test with 1000+ tiddlers

**Estimated Effort**: 2-3 weeks

---

### Phase 3: Initial Setup & Multi-Wiki
**Goal**: New client setup and remote wiki discovery

**Components**:
- ✅ S3 registry management
- ✅ Initial sync from S3 (download wiki)
- ✅ HTML snapshot upload/download
- ✅ Remote wiki browser UI
- ✅ Selective wiki sync

**Deliverables**:
1. Registry management in S3SyncManager
2. initial_sync_from_s3() implementation
3. upload_html_snapshot() implementation
4. React component: RemoteWikiBrowser
5. Setup wizard for new clients

**Testing**:
- Test initial download on fresh client
- Test HTML snapshot restoration
- Test registry updates
- Multi-wiki sync scenarios

**Estimated Effort**: 1-2 weeks

---

### Phase 4: Polish & Optimization
**Goal**: Production-ready reliability and performance

**Components**:
- ✅ Compression optimization
- ✅ Batch operations for multiple tiddlers
- ✅ S3 cost optimization (lifecycle policies)
- ✅ Better error messages and logging
- ✅ Performance metrics
- ✅ Version history browser

**Deliverables**:
1. Optimized compression (ZSTD vs GZIP benchmarks)
2. Batch upload/download operations
3. Detailed sync logs
4. React component: VersionHistoryBrowser
5. Performance dashboard

**Testing**:
- Performance benchmarks
- Cost analysis
- Stress testing with large wikis
- Long-running sync stability

**Estimated Effort**: 1-2 weeks

---

**Total Estimated Timeline**: 6-10 weeks for full implementation

---

## 10. Testing Strategy

### 10.1 Unit Tests

```python
# tests/test_s3_sync_manager.py
import unittest
from src.api.s3_sync_manager import S3SyncManager

class TestS3SyncManager(unittest.TestCase):
    
    def setUp(self):
        self.wiki_id = "test-wiki-123"
        self.s3_manager = S3SyncManager(self.wiki_id, mock_s3_config)
    
    def test_push_single_tiddler(self):
        """Test pushing a single tiddler to S3"""
        result = self.s3_manager.push_to_s3()
        self.assertEqual(result['status'], 'success')
        self.assertEqual(len(result['uploaded']), 1)
    
    def test_pull_modified_tiddler(self):
        """Test pulling modified tiddler from S3"""
        # Setup: modify tiddler in S3
        # Execute: pull from S3
        # Assert: local tiddler updated
        pass
    
    def test_conflict_resolution_lww(self):
        """Test Last-Write-Wins conflict resolution"""
        # Setup: create conflict scenario
        # Execute: sync
        # Assert: newer version wins
        pass
```

### 10.2 Integration Tests

```python
# tests/integration/test_multi_client_sync.py
class TestMultiClientSync(unittest.TestCase):
    
    def test_two_clients_sync(self):
        """Test sync between two clients"""
        
        # Setup: Create two client instances
        client_a = create_test_client("client-a")
        client_b = create_test_client("client-b")
        
        # Client A: Create tiddler
        client_a.create_tiddler("TestNote", "Content from A")
        client_a.sync_to_s3()
        
        # Client B: Pull changes
        client_b.pull_from_s3()
        
        # Assert: Client B has the tiddler
        tiddler = client_b.get_tiddler("TestNote")
        self.assertEqual(tiddler['text'], "Content from A")
    
    def test_offline_then_sync(self):
        """Test offline edits followed by sync"""
        # Simulate network failure
        # Make local edits
        # Restore network
        # Verify queued operations execute
        pass
```

### 10.3 End-to-End Tests

```python
# tests/e2e/test_full_workflow.py
class TestE2EWorkflow(unittest.TestCase):
    
    def test_new_client_setup(self):
        """Test complete new client setup from S3"""
        
        # Setup: Existing wiki in S3
        setup_s3_wiki("wiki-123", num_tiddlers=100)
        
        # Execute: New client downloads wiki
        client = create_fresh_client()
        client.download_remote_wiki("wiki-123")
        
        # Assert: All tiddlers downloaded
        local_count = client.get_tiddler_count()
        self.assertEqual(local_count, 100)
    
    def test_large_wiki_sync(self):
        """Test sync with large wiki (1000+ tiddlers)"""
        # Create large wiki
        # Measure sync performance
        # Assert: completes within acceptable time
        pass
```

### 10.4 Performance Benchmarks

```python
# benchmarks/sync_performance.py
def benchmark_push_performance():
    """Measure push performance with varying tiddler counts"""
    
    results = []
    for count in [10, 50, 100, 500, 1000]:
        start = time.time()
        push_n_tiddlers(count)
        elapsed = time.time() - start
        
        results.append({
            'tiddler_count': count,
            'elapsed_seconds': elapsed,
            'tiddlers_per_second': count / elapsed
        })
    
    print_benchmark_results(results)
```

---

## Appendix A: Dependencies

### Python Libraries

```txt
# requirements.txt additions
boto3>=1.26.0          # AWS SDK for Python
botocore>=1.29.0       # AWS low-level interface
```

**Note**: No compression or encryption libraries needed for initial phases.

### AWS Resources

- **Required**: S3 Bucket with versioning enabled
- **Required**: IAM User with S3 permissions (see Section 7.2 for IAM policy)
- **Optional (Phase 11.2)**: S3 Inventory + AWS Glue + Athena for analytics

---

## Appendix B: Configuration

**S3 Configuration** (stored in SQLite `s3_config` table):
```python
{
    "bucket_name": "my-wiki-bucket",
    "region": "us-east-1",
    "access_key_id": "AKIAIOSFODNN7EXAMPLE",
    "secret_access_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
    "enabled": True
}
```

**Sync Settings** (defaults, can be made configurable):
- Poll interval: 30-60 seconds
- Offline queue retry: 3 attempts with exponential backoff
- HTML snapshot upload: Daily
- Manifest cache with ETag validation

---

## Appendix C: Mermaid Diagrams

### Complete System Architecture

```mermaid
graph TB
    subgraph "Client A"
        A1[TiddlyWiki UI]
        A2[Sync Adaptor JS]
        A3[PyWebView Bridge]
        A4[WikiWindowAPI]
        A5[TiddlerStore SQLite]
        A6[S3SyncManager]
        A7[SyncCoordinator Thread]
    end
    
    subgraph "S3 Cloud Storage"
        S1[S3 Bucket]
        S2[Versioned Tiddlers]
        S3[HTML Snapshots]
        S4[Manifests]
    end
    
    subgraph "Client B"
        B1[TiddlyWiki UI]
        B2[Sync Adaptor JS]
        B3[PyWebView Bridge]
        B4[WikiWindowAPI]
        B5[TiddlerStore SQLite]
        B6[S3SyncManager]
        B7[SyncCoordinator Thread]
    end
    
    A1 <--> A2
    A2 <--> A3
    A3 <--> A4
    A4 <--> A5
    A5 <--> A6
    A6 <--> S1
    A7 --> A6
    
    B1 <--> B2
    B2 <--> B3
    B3 <--> B4
    B4 <--> B5
    B5 <--> B6
    B6 <--> S1
    B7 --> B6
    
    S1 --> S2
    S1 --> S3
    S1 --> S4
    
    style S1 fill:#ff9900
    style A5 fill:#ffe1e1
    style B5 fill:#ffe1e1
```

---

## Summary

This updated design document reflects the finalized architecture for implementing S3-based remote synchronization for the TiddlyWiki PyWebView application.

**Core Architecture Principles**:
1. **S3 as Source of Truth**: Persistent storage accessible across all devices and future services (Lambda, etc.)
2. **TiddlyWiki → S3 Real-Time**: Direct upload immediately on every save (when online)
3. **SQLite as Local Backup**: Persistence for offline scenarios and startup hydration
4. **Offline Queue in SQLite**: Failed uploads queued for retry when network restored
5. **Manifest-Based Sync**: Efficient pull using manifest.json (single API call for all timestamps)
6. **Atomic Manifest Updates**: ETag-based conditional writes prevent race conditions
7. **30-60 Second Polling**: Practical sync latency for single-user multi-device scenario

**Key Design Decisions**:
- ✅ No compression (simplicity over bandwidth)
- ✅ Tiddler modified timestamps for conflict resolution (not S3 object timestamps)
- ✅ S3 credentials in SQLite (not environment variables)
- ✅ TiddlyWiki plugin unchanged (S3 sync is transparent)
- ✅ React app only handles S3 configuration (not per-wiki sync)
- ✅ Manifest polling is the final solution (no SNS/SQS/IoT Core complexity)

**Ready for Phase 1 Implementation**: The design is complete and addresses all requirements for single-user multi-device synchronization with S3 as the persistent source of truth.
