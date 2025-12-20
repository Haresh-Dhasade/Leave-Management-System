document.addEventListener('DOMContentLoaded', function() {
    const isApprovedCheckbox = document.getElementById('id_is_approved');
    const isRejectedCheckbox = document.getElementById('id_is_rejected');
    const statusInput = document.getElementById('id_status');
    const statusDisplay = document.querySelector('.field-status p');

    function updateStatus() {
        if (isApprovedCheckbox.checked) {
            statusInput.value = 'approved';
            if (statusDisplay) statusDisplay.textContent = 'approved';
            isRejectedCheckbox.checked = false;
        } else if (isRejectedCheckbox.checked) {
            statusInput.value = 'rejected';
            if (statusDisplay) statusDisplay.textContent = 'rejected';
            isApprovedCheckbox.checked = false;
        } else {
            statusInput.value = 'pending';
            if (statusDisplay) statusDisplay.textContent = 'pending';
        }
    }

    isApprovedCheckbox.addEventListener('change', updateStatus);
    isRejectedCheckbox.addEventListener('change', updateStatus);
});
