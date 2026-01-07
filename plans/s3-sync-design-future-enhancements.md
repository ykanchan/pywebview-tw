## 11. Future Enhancements

### 11.1 Optimized Polling Strategies

**Adaptive Polling Interval**:
- **Active mode**: Poll every 10-15 seconds when app is in focus and recent changes detected
- **Idle mode**: Slow down to 60 seconds when no activity
- **On-demand**: Trigger immediate check on app focus/resume

**Manifest Caching with ETags**:
```python
def download_manifest_if_changed(wiki_id):
    """Download manifest only if it has changed"""
    
    # Get cached manifest ETag
    cached_etag = get_cached_manifest_etag(wiki_id)
    
    # Request with If-None-Match (S3 returns 304 if unchanged)
    response = s3_client.get_object(
        Bucket=bucket_name,
        Key=f"wikis/{wiki_id}/manifest.json",
        IfNoneMatch=cached_etag
    )
    
    if response['ResponseMetadata']['HTTPStatusCode'] == 304:
        # Not modified - use cached manifest
        return get_cached_manifest(wiki_id), False
    else:
        # Modified - download and cache
        manifest = json.loads(response['Body'].read())
        cache_manifest(wiki_id, manifest, response['ETag'])
        return manifest, True
```

**Benefits**:
- Reduces bandwidth (no download if manifest unchanged)
- Reduces S3 costs (304 responses are cheaper)
- Maintains good sync latency with smart polling

---

### 11.2 S3 Metadata Tables with AWS Athena

**Use Case**: Query tiddler metadata across all wikis using SQL without downloading objects.

**Setup**:
1. Enable **S3 Inventory** on the bucket (generates manifest of all objects daily/weekly)
2. Create **AWS Glue Crawler** to catalog S3 inventory data
3. Query using **AWS Athena** (serverless SQL)

**Example Queries**:
```sql
-- Find all tiddlers modified in the last 7 days across all wikis
SELECT 
    key AS s3_key,
    last_modified_date,
    size
FROM s3_inventory_table
WHERE 
    key LIKE 'wikis/%/tiddlers/%.json'
    AND last_modified_date > CURRENT_DATE - INTERVAL '7' DAY
ORDER BY last_modified_date DESC;

-- Analyze storage usage per wiki
SELECT 
    REGEXP_EXTRACT(key, 'wikis/([^/]+)/', 1) AS wiki_id,
    COUNT(*) AS tiddler_count,
    SUM(size) AS total_bytes
FROM s3_inventory_table
WHERE key LIKE 'wikis/%/tiddlers/%.json'
GROUP BY REGEXP_EXTRACT(key, 'wikis/([^/]+)/', 1);
```

**Benefits**:
- Analytics without downloading tiddlers
- Efficient cross-wiki searches
- Cost-effective for large-scale data analysis
- No real-time sync infrastructure needed

**Limitations**:
- Inventory updates are not real-time (daily/weekly)
- Best for analytics, not sync operations
- Adds AWS Glue/Athena costs

---

### 11.3 Collaborative Editing

**Operational Transform (OT)** or **CRDTs** for real-time collaboration:
- Track character-level changes
- Resolve simultaneous edits
- Show other users' cursors

**Challenge**: TiddlyWiki not designed for collaborative editing
**Alternative**: Lock-based editing (one user at a time per tiddler)

---

### 11.4 Alternative Cloud Providers

**Multi-Provider Support**:
- Google Cloud Storage
- Azure Blob Storage
- Dropbox
- Google Drive (via WebDAV)

**Implementation**:
- Abstract storage interface
- Provider-specific implementations
- Unified configuration

---

### 11.5 Advanced Conflict Resolution

**Beyond LWW**:
- Three-way merge for text content
- Manual conflict resolution UI
- Conflict history view
- Keep both versions option

---

### 11.6 Encryption & Privacy

**Client-Side Encryption**:
- Encrypt tiddler content before uploading
- Zero-knowledge architecture
- Key management (password-derived or keyfile)

**Benefits**:
- True privacy (S3 can't read content)
- Compliance with data protection regulations
