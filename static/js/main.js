/* ---------- CREATE CUSTOMER MODAL ---------- */
function bindCreateModal () {
  const $modal   = $('#createUser');
  const $baseSel = $modal.find('#id_base_plan');
  const $addSel  = $modal.find('#id_add_on_plan');
  const $dueAmt  = $modal.find('#due_amount');
  const $dueDate = $modal.find('#due_date');

  // Initialise Select2
  $addSel.select2({
    dropdownParent: $modal,
    placeholder: 'Select Add‑on Plans',
    width: 'resolve',
    allowClear: true,
  });

  // Fetch plan info
  function refreshPlanInfo () {
    const baseId   = $baseSel.val() || '';
    const addonIds = $addSel.val() ? $addSel.val().join(',') : '';

    if (!baseId) {
      $dueAmt.val('');

      return;
    }

    fetch(`/dashboard/customers/plan-info/?base_plan=${baseId}&add_on_plan=${addonIds}`)
      .then(r => r.json())
      .then(data => {
        $dueAmt.val(data.due_amount || '');

      })
      .catch(err => console.error('plan‑info error', err));
  }

  // Bind events
  $baseSel.on('change', refreshPlanInfo);
  $addSel.on('change select2:select select2:unselect', refreshPlanInfo);

  // Initial fetch
  refreshPlanInfo();
}

$('#createUser').on('shown.bs.modal', bindCreateModal);

/* ---------- SELECT2 INIT FOR CREATE & EDIT ---------- */
$(document).ready(function () {
  $('#createUser').on('shown.bs.modal', function () {
    $('#addOnPlans').select2({
      dropdownParent: $('#createUser'),
      placeholder: 'Select Add-on Plans',
      searchResultLimit: 5,
      width: 'resolve',
      allowClear: true,
    });
  });

  $('#EditUser').on('shown.bs.modal', function () {
    $('#EditAddons').select2({
      dropdownParent: $('#EditUser'),
      placeholder: 'Edit Add-on Plans',
      searchResultLimit: 5,
      width: 'resolve',
      allowClear: true,
    });
  });
});

/* ---------- DATATABLES ---------- */
document.addEventListener("DOMContentLoaded", function () {
  new DataTable("#myTable", {
    responsive: true,
    searching: false,
    lengthChange: false,
  });

  new DataTable("#PaymentHistoryTable", {
    responsive: true,
    searching: false,
    lengthChange: false,
  });

  new DataTable("#CustomerListTable", {
    responsive: true,
    searching: false,
    lengthChange: false,
  });

  new DataTable("#RecentPaymentTable", {
    responsive: true,
    searching: false,
    lengthChange: false,
  });
});
