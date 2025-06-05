document.addEventListener('DOMContentLoaded', function() {
    // Add page content preview functionality
    function initializePageContentPreview() {
        const pageSelect = document.getElementById('id_page');
        const contentContainer = document.querySelector('.field-content');
        
        if (pageSelect && contentContainer) {
            pageSelect.addEventListener('change', function() {
                const selectedPage = this.value;
                
                // Make AJAX request to get existing content
                fetch(`/admin/website/get-page-content/?page=${selectedPage}`)
                    .then(response => response.json())
                    .then(data => {
                        // Update the form with existing content
                        const contentArea = document.querySelector('#id_content');
                        if (contentArea && data.content) {
                            contentArea.value = data.content;
                        }
                        
                        // Show preview of the page
                        showPagePreview(selectedPage);
                    });
            });
        }
    }

    // FAQ Management
    function initializeFAQManager() {
        const pageSelect = document.getElementById('id_page');
        const faqContainer = document.querySelector('.field-question');
        
        if (pageSelect && faqContainer) {
            pageSelect.addEventListener('change', function() {
                const selectedPage = this.value;
                
                // Make AJAX request to get existing FAQs
                fetch(`/admin/website/get-page-faqs/?page=${selectedPage}`)
                    .then(response => response.json())
                    .then(data => {
                        // Update FAQ list
                        updateFAQList(data.faqs);
                        
                        // Show preview of the page with FAQs
                        showPagePreview(selectedPage);
                    });
            });
        }
    }

    function updateFAQList(faqs) {
        const container = document.querySelector('.faq-list') || createFAQList();
        
        container.innerHTML = faqs.map(faq => `
            <div class="faq-item">
                <div class="faq-preview">
                    <h3>${faq.question}</h3>
                    <p>${faq.answer}</p>
                </div>
                <div class="faq-actions">
                    <button onclick="editFAQ(${faq.id})" class="button">Edit</button>
                    <button onclick="deleteFAQ(${faq.id})" class="button">Delete</button>
                </div>
            </div>
        `).join('');
    }

    function createFAQList() {
        const container = document.createElement('div');
        container.className = 'faq-list';
        document.querySelector('.module').appendChild(container);
        return container;
    }

    // Preview functionality
    function showPagePreview(page) {
        const previewFrame = document.querySelector('.preview-frame') || createPreviewFrame();
        previewFrame.src = `/${page}/`;
    }

    function createPreviewFrame() {
        const container = document.createElement('div');
        container.className = 'preview-container';
        
        const frame = document.createElement('iframe');
        frame.className = 'preview-frame';
        
        container.appendChild(frame);
        document.body.appendChild(container);
        
        return frame;
    }

    // Initialize the preview features
    function initializePreview() {
        const previewButtons = document.querySelectorAll('.preview-btn');
        
        previewButtons.forEach(button => {
            button.addEventListener('click', function() {
                const page = this.dataset.page;
                const id = this.dataset.id;
                
                showPagePreview(page);
            });
        });
    }

    // Edit content directly from preview
    function initializeInPlaceEditing() {
        const previewFrame = document.querySelector('.preview-frame');
        
        if (previewFrame) {
            previewFrame.addEventListener('load', function() {
                const frameDoc = this.contentDocument || this.contentWindow.document;
                const editableElements = frameDoc.querySelectorAll('[data-editable]');
                
                editableElements.forEach(element => {
                    element.addEventListener('click', function() {
                        const contentId = this.dataset.id;
                        const contentType = this.dataset.type;
                        
                        // Open edit form in admin
                        window.location.href = `/admin/website/${contentType}/${contentId}/change/`;
                    });
                });
            });
        }
    }

    // Initialize all features
    initializePageContentPreview();
    initializeFAQManager();
    initializePreview();
    initializeInPlaceEditing();
});