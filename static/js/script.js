document.body.addEventListener('closeModal', function () {
    document.querySelectorAll('.modal.show').forEach(m => {
        bootstrap.Modal.getInstance(m).hide();
    });
});

// 🔥 FIX: run BEFORE modal is hidden
document.addEventListener('hide.bs.modal', function (event) {
    if (event.target.contains(document.activeElement)) {
        document.activeElement.blur();
    }
}); 
