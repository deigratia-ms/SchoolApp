django.jQuery(document).ready(function($) {
    function toggleExecutivePosition() {
        var staffType = $('input[name="staff_type"]:checked').val();
        var executivePositionField = $('.executive-position-field').closest('.form-row');
        
        if (staffType === 'executive') {
            executivePositionField.show();
        } else {
            executivePositionField.hide();
            $('.executive-position-field').val('');
        }
    }

    // Initial state
    toggleExecutivePosition();

    // On staff type change
    $('input[name="staff_type"]').change(function() {
        toggleExecutivePosition();
    });
});