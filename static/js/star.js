// Function to toggle star on an item
async function toggleStar(itemType, itemId, event = null) {
    if (event) event.preventDefault();
    
    if (!isLoggedIn()) {
        showLoginModal();
        return;
    }

    const starButton = document.querySelector(`.star-btn[data-item-type="${itemType}"][data-item-id="${itemId}"]`);
    const starCount = starButton ? starButton.querySelector('.star-count') : null;
    
    if (!starButton) {
        console.error('Star button not found');
        return;
    }
    
    // Disable the button while processing
    starButton.disabled = true;
    
    try {
        const response = await fetch(`/api/star/${itemType}/${itemId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            },
            credentials: 'same-origin'
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || `HTTP error! status: ${response.status}`);
        }
        
        // Update star button appearance
        const icon = starButton.querySelector('i');
        const text = starButton.querySelector('span:not(.star-count)');
        
        if (data.starred) {
            starButton.classList.add('starred');
            if (icon) icon.classList.replace('far', 'fas');
            if (text) text.textContent = ' Starred';
        } else {
            starButton.classList.remove('starred');
            if (icon) icon.classList.replace('fas', 'far');
            if (text) text.textContent = ' Star';
        }
        
        // Update star count if available
        if (data.star_count !== undefined && starCount) {
            starCount.textContent = data.star_count;
        }
        
        // Show feedback
        if (data.message) {
            showToast(data.message);
        } else {
            showToast(data.starred ? 'Added to your stars' : 'Removed from your stars');
        }
        
        return data;
    } catch (error) {
        console.error('Error toggling star:', error);
        showToast('Failed to update star', 'error');
        return { error: error.message };
    } finally {
        if (starButton) {
            starButton.disabled = false;
        }
    }
}

// Initialize star buttons using event delegation
document.addEventListener('DOMContentLoaded', function() {
    // Handle clicks on star buttons using event delegation
    document.addEventListener('click', function(e) {
        const starButton = e.target.closest('.star-btn');
        if (!starButton) return;
        
        e.preventDefault();
        const itemType = starButton.getAttribute('data-item-type');
        const itemId = starButton.getAttribute('data-item-id');
        if (itemType && itemId) {
            toggleStar(itemType, itemId, e);
        }
    });
});

// Helper function to check if user is logged in
function isLoggedIn() {
    return document.body.getAttribute('data-user-id') !== 'None';
}

// Helper function to show toast messages
function showToast(message, type = 'success') {
    // You can implement a toast system or use alert for now
    alert(message);
}

// Helper function to show login modal
function showLoginModal() {
    // You can implement a login modal or redirect to login page
    window.location.href = '/login?next=' + encodeURIComponent(window.location.pathname);
}
