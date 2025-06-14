/**
 * Dynamic Section Filtering for PageContent Admin
 * Filters section dropdown based on selected page
 */

(function($) {
    'use strict';

    console.log('PageContent admin script starting to load...');

    // Define page-to-sections mapping (using actual model field values)
    const PAGE_SECTIONS = {
        'home': [
            'hero',
            'about_preview',
            'featured_programs',
            'why_choose_us'
        ],
        'about': [
            'about_hero',
            'mission',
            'vision',
            'story',
            'montessori_method',
            'values'
        ],
        'academics': [
            'academics_hero',
            'curriculum_approach',
            'assessment_intro',
            'cta_section'
        ],
        'admissions': [
            'hero',  // Admissions uses 'hero' not 'admissions_hero'
            'admission_process',
            'requirements',
            'fees',
            'scholarships'
        ],
        'events': [
            'events_hero',
            'events_newsletter',
            'events_cta',
            'events_calendar'
        ],
        'news': [
            'news_hero'
        ],
        'contact': [
            'contact_hero'
        ],
        'staff': [
            'staff_hero'
        ],
        'career': [
            'career_hero',
            'career_intro'
        ],
        'calendar': [
            'calendar_hero',
            'calendar_content'
        ],
        'privacy': [
            'privacy_hero',
            'privacy_content'
        ],
        'terms': [
            'terms_hero',
            'terms_content'
        ],
        'faq': [
            'faq_hero'
        ]
    };

    // Section display names for better UX
    const SECTION_NAMES = {
        'hero': 'Hero Section',
        'about_preview': 'About Preview',
        'featured_programs': 'Featured Programs',
        'why_choose_us': 'Why Choose Us',
        'about_hero': 'About Hero Section',
        'mission': 'Mission Statement',
        'vision': 'Vision Statement',
        'story': 'Our Story',
        'montessori_method': 'Montessori Method',
        'values': 'Our Values',
        'academics_hero': 'Academics Hero Section',
        'curriculum_image': 'Curriculum Approach Image',
        'assessment_intro': 'Assessment Introduction',
        'cta_section': 'Academics Call to Action',
        'admission_process': 'Admission Process',
        'requirements': 'Requirements',
        'fees': 'Fees and Tuition',
        'scholarships': 'Scholarships',
        'events_hero': 'Events Hero Section',
        'events_newsletter': 'Events Newsletter Section',
        'events_cta': 'Events Call to Action',
        'events_calendar': 'Events Calendar Placeholder',
        'news_hero': 'News Hero Section',
        'contact_hero': 'Contact Hero Section',
        'staff_hero': 'Staff Hero Section',
        'career_hero': 'Career Hero Section',
        'career_intro': 'Career Introduction',
        'calendar_hero': 'Calendar Hero Section',
        'calendar_content': 'Calendar Content',
        'privacy_hero': 'Privacy Policy Hero Section',
        'privacy_content': 'Privacy Policy Content',
        'terms_hero': 'Terms of Service Hero Section',
        'terms_content': 'Terms of Service Content',
        'faq_hero': 'FAQ Hero Section'
    };

    function filterSections() {
        const pageSelect = $('#id_page');
        const sectionSelect = $('#id_section');

        if (!pageSelect.length || !sectionSelect.length) {
            return;
        }

        const selectedPage = pageSelect.val();
        const currentSection = sectionSelect.val();

        console.log('Filtering sections for page:', selectedPage); // Debug log

        // Store all original options if not already stored
        if (!sectionSelect.data('original-options')) {
            const originalOptions = sectionSelect.find('option').clone();
            sectionSelect.data('original-options', originalOptions);
            console.log('Stored original options:', originalOptions.length); // Debug log
        }

        // Clear ALL options first
        sectionSelect.empty();

        if (!selectedPage) {
            // No page selected - disable dropdown and show helpful message
            sectionSelect.prop('disabled', true);
            sectionSelect.append('<option value="">Please select a page first</option>');
            sectionSelect.addClass('disabled-until-page-selected');
        } else {
            // Page selected - enable dropdown and filter sections
            sectionSelect.prop('disabled', false);
            sectionSelect.removeClass('disabled-until-page-selected');

            // Add empty option first
            sectionSelect.append('<option value="">---------</option>');

            if (PAGE_SECTIONS[selectedPage]) {
                const validSections = PAGE_SECTIONS[selectedPage];
                console.log('Valid sections for', selectedPage, ':', validSections); // Debug log

                // Add only the valid sections for this page
                validSections.forEach(function(sectionValue) {
                    const displayName = SECTION_NAMES[sectionValue] || sectionValue;
                    const option = $('<option></option>')
                        .attr('value', sectionValue)
                        .text(displayName);
                    sectionSelect.append(option);
                });

                // Restore the current selection if it's still valid
                if (currentSection && validSections.includes(currentSection)) {
                    sectionSelect.val(currentSection);
                }

                console.log('Added', validSections.length, 'sections to dropdown'); // Debug log
            } else {
                // Fallback: if page not in our mapping, show all sections
                console.log('Page not in mapping, showing all sections'); // Debug log
                const originalOptions = sectionSelect.data('original-options');
                originalOptions.each(function() {
                    const option = $(this);
                    if (option.val()) {
                        sectionSelect.append(option.clone());
                    }
                });
                sectionSelect.val(currentSection);
            }
        }
    }

    // Initialize when the page loads
    $(document).ready(function() {
        console.log('PageContent admin script loaded successfully!'); // Debug log
        // Add some helpful styling
        $('<style>')
            .prop('type', 'text/css')
            .html(`
                .field-section .help {
                    color: #666;
                    font-style: italic;
                    margin-top: 5px;
                }
                .section-filter-info {
                    background: #e7f3ff;
                    border: 1px solid #b3d9ff;
                    padding: 10px;
                    margin: 10px 0;
                    border-radius: 4px;
                    font-size: 12px;
                }
                .section-count {
                    color: #666;
                    font-size: 11px;
                    margin-left: 10px;
                }
                .disabled-until-page-selected {
                    background-color: #f5f5f5 !important;
                    color: #999 !important;
                    cursor: not-allowed !important;
                }
                .disabled-until-page-selected:hover {
                    background-color: #f5f5f5 !important;
                }
                #id_section:disabled {
                    opacity: 0.6;
                }
            `)
            .appendTo('head');

        // Add helpful information
        const pageField = $('.field-page');
        if (pageField.length) {
            pageField.after(`
                <div class="section-filter-info">
                    <strong>💡 Smart Section Filtering:</strong> Select a page first, then choose from the relevant sections for that page.
                    This prevents selecting wrong sections for the wrong pages and makes content management easier.
                </div>
            `);
        }

        // Add section count indicator
        const sectionField = $('.field-section');
        if (sectionField.length) {
            sectionField.find('label').append('<span class="section-count" id="section-count"></span>');
        }

        // Check if the required elements exist
        const pageSelect = $('#id_page');
        const sectionSelect = $('#id_section');

        if (!pageSelect.length) {
            console.log('Page select element not found!');
            return;
        }

        if (!sectionSelect.length) {
            console.log('Section select element not found!');
            return;
        }

        console.log('Found page and section elements, setting up filtering...');

        // Bind the change event
        pageSelect.on('change', function() {
            console.log('Page changed to:', $(this).val());
            filterSections();
            updateSectionCount();
        });

        // Run initial filter
        filterSections();
        updateSectionCount();
    });

    function updateSectionCount() {
        const sectionSelect = $('#id_section');
        const countElement = $('#section-count');
        const optionCount = sectionSelect.find('option:not([value=""])').length;

        if (countElement.length && optionCount > 0) {
            countElement.text(`(${optionCount} available sections)`);
        }
    }

})(django.jQuery);
