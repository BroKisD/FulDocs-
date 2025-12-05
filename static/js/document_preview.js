// Initialize document preview modal
const previewModal = new bootstrap.Modal(document.getElementById('documentPreviewModal'));

// Function to show document preview
async function showDocumentPreview(docId) {
  const previewContent = document.getElementById('previewContent');
  const previewLoading = document.getElementById('previewLoading');
  const previewError = document.getElementById('previewError');
  const filePreview = document.getElementById('filePreview');
  const downloadBtn = document.getElementById('downloadBtn');
  const previewTitle = document.getElementById('previewTitle');
  const previewAuthor = document.getElementById('previewAuthor');
  const previewDate = document.getElementById('previewDate');
  const previewDescription = document.getElementById('previewDescription');
  
  // Reset UI
  previewContent.style.display = 'none';
  previewLoading.style.display = 'block';
  previewError.style.display = 'none';
  filePreview.innerHTML = '';
  
  try {
    // Show the modal
    previewModal.show();
    
    // Fetch document details
    const response = await fetch(`/document/preview/${docId}`);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const doc = await response.json();
    
    // Update document info
    if (previewTitle) previewTitle.textContent = doc.title;
    if (previewAuthor) previewAuthor.textContent = doc.author || 'Unknown';
    if (previewDate) {
      const date = new Date(doc.created_at);
      previewDate.textContent = date.toLocaleDateString();
    }
    if (previewDescription) previewDescription.textContent = doc.description || '';
    
    // Set download link
    if (downloadBtn && doc.file_path) {
      downloadBtn.href = `/uploads/${encodeURIComponent(doc.file_path)}`;
      downloadBtn.download = doc.file_path.split('/').pop();
    }
    
    // Handle different file types
    if (doc.file_path) {
      const fileType = doc.file_type || doc.file_path.split('.').pop().toLowerCase();
      
      if (['jpg', 'jpeg', 'png', 'gif'].includes(fileType)) {
        // Image preview
        filePreview.innerHTML = `
          <div class="text-center">
            <img src="/uploads/${encodeURIComponent(doc.file_path)}" 
                 alt="${doc.title}" 
                 class="img-fluid rounded">
          </div>`;
      } 
      else if (fileType === 'pdf') {
        // PDF preview using iframe
        filePreview.innerHTML = `
          <div class="ratio ratio-16x9">
            <iframe src="/uploads/${encodeURIComponent(doc.file_path)}" 
                    style="width: 100%; height: 100%; border: 1px solid #dee2e6; border-radius: 0.25rem;">
            </iframe>
          </div>`;
      }
      else if (['html', 'htm'].includes(fileType)) {
        // HTML preview using iframe
        filePreview.innerHTML = `
          <div class="ratio ratio-16x9">
            <iframe src="/document/html/${encodeURIComponent(doc.file_path)}" 
                    sandbox="allow-same-origin allow-scripts"
                    style="width: 100%; height: 100%; border: 1px solid #dee2e6; border-radius: 0.25rem;">
            </iframe>
          </div>`;
      }
      else {
        // Unsupported file type
        filePreview.innerHTML = `
          <div class="text-center py-4">
            <i class="fas fa-file-alt fa-4x text-muted mb-3"></i>
            <p class="text-muted">Preview not available for this file type</p>
            <p class="small">File type: ${fileType}</p>
          </div>`;
      }
    }
    
    // Show the content
    previewLoading.style.display = 'none';
    previewContent.style.display = 'block';
    
  } catch (error) {
    console.error('Error loading document preview:', error);
    previewLoading.style.display = 'none';
    previewError.textContent = 'Failed to load document preview. ' + (error.message || 'Please try again later.');
    previewError.style.display = 'block';
  }
}

// Initialize event listeners when the DOM is fully loaded
document.addEventListener('DOMContentLoaded', function() {
  // Handle document preview button clicks in search results
  document.addEventListener('click', function(event) {
    const previewBtn = event.target.closest('.preview-doc');
    if (previewBtn) {
      event.preventDefault();
      const docId = previewBtn.getAttribute('data-doc-id');
      if (docId) {
        showDocumentPreview(docId);
      }
    }
  });
});
