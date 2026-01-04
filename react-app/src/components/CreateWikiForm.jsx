import React, { useState } from 'react';
import '../styles/CreateWikiForm.css';

const CreateWikiForm = ({ onSubmit, onCancel }) => {
  const [formData, setFormData] = useState({
    name: '',
    description: ''
  });
  const [errors, setErrors] = useState({});
  const [isSubmitting, setIsSubmitting] = useState(false);

  const validateForm = () => {
    const newErrors = {};
    
    if (!formData.name.trim()) {
      newErrors.name = 'Wiki name is required';
    } else if (formData.name.length > 50) {
      newErrors.name = 'Wiki name must be 50 characters or less';
    }
    
    if (formData.description.length > 200) {
      newErrors.description = 'Description must be 200 characters or less';
    }
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (validateForm()) {
      setIsSubmitting(true);
      try {
        await onSubmit(formData);
        // Form will be closed by parent component on success
      } catch (error) {
        setErrors({ submit: 'Failed to create wiki. Please try again.' });
      } finally {
        setIsSubmitting(false);
      }
    }
  };

  const handleInputChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    // Clear error when user starts typing
    if (errors[field]) {
      setErrors(prev => ({ ...prev, [field]: '' }));
    }
  };

  const handleOverlayClick = (e) => {
    if (e.target === e.currentTarget) {
      onCancel();
    }
  };

  return (
    <div className="modal-overlay" onClick={handleOverlayClick}>
      <div className="modal-content">
        <form onSubmit={handleSubmit} className="create-wiki-form">
          <div className="form-header">
            <h2>Create New Wiki</h2>
            <button 
              type="button" 
              className="close-button" 
              onClick={onCancel}
              aria-label="Close"
            >
              ×
            </button>
          </div>
          
          <div className="form-body">
            <div className="form-group">
              <label htmlFor="wiki-name">
                Wiki Name <span className="required">*</span>
              </label>
              <input
                id="wiki-name"
                type="text"
                value={formData.name}
                onChange={(e) => handleInputChange('name', e.target.value)}
                placeholder="Enter wiki name"
                className={errors.name ? 'error' : ''}
                disabled={isSubmitting}
                autoFocus
              />
              {errors.name && <span className="error-text">{errors.name}</span>}
              <span className="char-count">{formData.name.length}/50</span>
            </div>

            <div className="form-group">
              <label htmlFor="wiki-description">Description</label>
              <textarea
                id="wiki-description"
                value={formData.description}
                onChange={(e) => handleInputChange('description', e.target.value)}
                placeholder="Enter wiki description (optional)"
                rows="4"
                className={errors.description ? 'error' : ''}
                disabled={isSubmitting}
              />
              {errors.description && <span className="error-text">{errors.description}</span>}
              <span className="char-count">{formData.description.length}/200</span>
            </div>

            {errors.submit && (
              <div className="error-message">
                {errors.submit}
              </div>
            )}
          </div>

          <div className="form-actions">
            <button 
              type="button" 
              className="btn btn-secondary" 
              onClick={onCancel}
              disabled={isSubmitting}
            >
              Cancel
            </button>
            <button 
              type="submit" 
              className="btn btn-primary"
              disabled={isSubmitting}
            >
              {isSubmitting ? 'Creating...' : 'Create Wiki'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default CreateWikiForm;
