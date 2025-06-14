document.addEventListener('DOMContentLoaded', function() {
    const showButtonsCheckbox = document.getElementById('id_show_buttons');
    const buttonConfigSections = document.querySelectorAll('.button-config');

    // Get button field elements
    const primaryButtonText = document.getElementById('id_primary_button_text');
    const primaryButtonUrl = document.getElementById('id_primary_button_url');
    const secondaryButtonText = document.getElementById('id_secondary_button_text');
    const secondaryButtonUrl = document.getElementById('id_secondary_button_url');

    function toggleButtonFields() {
        const isChecked = showButtonsCheckbox.checked;

        buttonConfigSections.forEach(function(section) {
            if (isChecked) {
                section.classList.remove('collapsed');
                section.style.display = 'block';
            } else {
                section.classList.add('collapsed');
                section.style.display = 'none';
            }
        });

        // If enabling buttons and fields are empty, populate with defaults
        if (isChecked) {
            if (primaryButtonText && !primaryButtonText.value.trim()) {
                primaryButtonText.value = 'Apply Now';
            }
            if (primaryButtonUrl && !primaryButtonUrl.value.trim()) {
                primaryButtonUrl.value = '/admissions/';
            }
            if (secondaryButtonText && !secondaryButtonText.value.trim()) {
                secondaryButtonText.value = 'Contact Us';
            }
            if (secondaryButtonUrl && !secondaryButtonUrl.value.trim()) {
                secondaryButtonUrl.value = '/contact/';
            }
        }
    }

    // Initial state
    if (showButtonsCheckbox) {
        toggleButtonFields();

        // Listen for changes
        showButtonsCheckbox.addEventListener('change', toggleButtonFields);
    }

    // Add helpful styling and quick-fill buttons
    const style = document.createElement('style');
    style.textContent = `
        .button-config.collapsed {
            display: none !important;
        }

        .field-primary_button_url input,
        .field-secondary_button_url input {
            width: 100%;
            max-width: 400px;
        }

        .help {
            font-size: 11px;
            color: #666;
            margin-top: 5px;
        }

        .quick-fill-buttons {
            margin-top: 5px;
            margin-bottom: 10px;
        }

        .quick-fill-btn {
            background: #f0f0f0;
            border: 1px solid #ccc;
            padding: 2px 6px;
            margin: 2px;
            font-size: 10px;
            cursor: pointer;
            border-radius: 3px;
        }

        .quick-fill-btn:hover {
            background: #e0e0e0;
        }
    `;
    document.head.appendChild(style);

    // Add quick-fill buttons for common values
    function addQuickFillButtons() {
        // Primary button text quick fills
        if (primaryButtonText) {
            const primaryTextQuickFills = document.createElement('div');
            primaryTextQuickFills.className = 'quick-fill-buttons';
            primaryTextQuickFills.innerHTML = `
                <small style="color: #666;">Quick fill:</small>
                <button type="button" class="quick-fill-btn" onclick="document.getElementById('id_primary_button_text').value='Apply Now'">Apply Now</button>
                <button type="button" class="quick-fill-btn" onclick="document.getElementById('id_primary_button_text').value='Learn More'">Learn More</button>
                <button type="button" class="quick-fill-btn" onclick="document.getElementById('id_primary_button_text').value='Get Started'">Get Started</button>
                <button type="button" class="quick-fill-btn" onclick="document.getElementById('id_primary_button_text').value='Enroll Now'">Enroll Now</button>
            `;
            primaryButtonText.parentNode.appendChild(primaryTextQuickFills);
        }

        // Primary button URL quick fills
        if (primaryButtonUrl) {
            const primaryUrlQuickFills = document.createElement('div');
            primaryUrlQuickFills.className = 'quick-fill-buttons';
            primaryUrlQuickFills.innerHTML = `
                <small style="color: #666;">Quick fill:</small>
                <button type="button" class="quick-fill-btn" onclick="document.getElementById('id_primary_button_url').value='/admissions/'">/admissions/</button>
                <button type="button" class="quick-fill-btn" onclick="document.getElementById('id_primary_button_url').value='/about/'">/about/</button>
                <button type="button" class="quick-fill-btn" onclick="document.getElementById('id_primary_button_url').value='/academics/'">/academics/</button>
                <button type="button" class="quick-fill-btn" onclick="document.getElementById('id_primary_button_url').value='/virtual-tour/'">/virtual-tour/</button>
            `;
            primaryButtonUrl.parentNode.appendChild(primaryUrlQuickFills);
        }

        // Secondary button text quick fills
        if (secondaryButtonText) {
            const secondaryTextQuickFills = document.createElement('div');
            secondaryTextQuickFills.className = 'quick-fill-buttons';
            secondaryTextQuickFills.innerHTML = `
                <small style="color: #666;">Quick fill:</small>
                <button type="button" class="quick-fill-btn" onclick="document.getElementById('id_secondary_button_text').value='Contact Us'">Contact Us</button>
                <button type="button" class="quick-fill-btn" onclick="document.getElementById('id_secondary_button_text').value='Call Now'">Call Now</button>
                <button type="button" class="quick-fill-btn" onclick="document.getElementById('id_secondary_button_text').value='Visit Us'">Visit Us</button>
                <button type="button" class="quick-fill-btn" onclick="document.getElementById('id_secondary_button_text').value=''">Clear</button>
            `;
            secondaryButtonText.parentNode.appendChild(secondaryTextQuickFills);
        }

        // Secondary button URL quick fills
        if (secondaryButtonUrl) {
            const secondaryUrlQuickFills = document.createElement('div');
            secondaryUrlQuickFills.className = 'quick-fill-buttons';
            secondaryUrlQuickFills.innerHTML = `
                <small style="color: #666;">Quick fill:</small>
                <button type="button" class="quick-fill-btn" onclick="document.getElementById('id_secondary_button_url').value='/contact/'">/contact/</button>
                <button type="button" class="quick-fill-btn" onclick="document.getElementById('id_secondary_button_url').value='tel:+233123456789'">Phone</button>
                <button type="button" class="quick-fill-btn" onclick="document.getElementById('id_secondary_button_url').value='mailto:info@deigratiams.edu.gh'">Email</button>
                <button type="button" class="quick-fill-btn" onclick="document.getElementById('id_secondary_button_url').value='/staff/'">Staff</button>
            `;
            secondaryButtonUrl.parentNode.appendChild(secondaryUrlQuickFills);
        }
    }

    // Add quick-fill buttons after a short delay to ensure DOM is ready
    setTimeout(addQuickFillButtons, 100);
});
