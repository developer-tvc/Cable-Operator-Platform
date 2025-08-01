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

///* ---------- DATATABLES ---------- */
//document.addEventListener("DOMContentLoaded", function () {
//  new DataTable("#myTable", {
//    responsive: true,
//    searching: false,
//    lengthChange: false,
//  });
//
//  new DataTable("#PaymentHistoryTable", {
//    responsive: true,
//    searching: false,
//    lengthChange: false,
//  });
//
//  new DataTable("#CustomerListTable", {
//    responsive: true,
//    searching: false,
//    lengthChange: false,
//  });
//
//  new DataTable("#RecentPaymentTable", {
//    responsive: true,
//    searching: false,
//    lengthChange: false,
//  });
//});

//Table//
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
  new DataTable("#PaymentManagementTable", {
    responsive: true,
    searching: false,
    lengthChange: false,
  });

  const toggle = document.getElementById("togglePassword");
  const passwordField = document.getElementById("id_password");

  toggle.addEventListener("click", function () {
    const type = passwordField.getAttribute("type") === "password" ? "text" : "password";
    passwordField.setAttribute("type", type);
    this.classList.toggle("fa-eye");
    this.classList.toggle("fa-eye-slash");
  });
  
});

//Success Modal//
//document.getElementById("formCreate").addEventListener("submit", function (e) {
//  e.preventDefault();
//
//  const createplanEl = document.getElementById("createplan");
//  const createplan = bootstrap.Modal.getInstance(createplanEl);
//
//
//  createplanEl.addEventListener( "hidden.bs.modal", function () {
//    const successModal = new bootstrap.Modal(document.getElementById("successModal"));
//    successModal.show();
//  },
//
//    { once: true }
//  );
//
//
//  createplan.hide();
//});

//Delete Modal//
const modal = new bootstrap.Modal(document.getElementById("DeactivateModal"));
const confirmBtn = document.getElementById("DelmodalConfirmBtn");
let formToSubmit = null;

// Handle all delete forms
document.querySelectorAll(".deleteForm").forEach((form) => {
  form.addEventListener("submit", function (e) {
    e.preventDefault(); // Always stop default

    formToSubmit = form; // Save the reference of the clicked form
    modal.show();        // Show confirmation modal
  });
});

// When user confirms deletion
confirmBtn.addEventListener("click", function () {
  if (formToSubmit) {
    formToSubmit.submit(); // Submit the stored form
    formToSubmit = null;   // Reset after submission
  }
});


//Edit prefill
let currentCustomerId = null;

async function loadCustomerData(customerId) {
    try {
        const response = await fetch(`/dashboard/customer/edit/${customerId}/`, {
            method: 'GET',
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        });

        if (!response.ok) throw new Error('Fetch failed');

        const data = await response.json();

         // Populate dropdowns with options first
        const baseSelect = document.getElementById('edit_base_plan');
        baseSelect.innerHTML = '<option value="">Select Base Plan</option>';
        data.base_plans.forEach(plan => {
            const option = document.createElement('option');
            option.value = plan.id;
            option.textContent = `${plan.name} - ₹${plan.price}`;
            baseSelect.appendChild(option);
        });

        // Populate Add-on Plan dropdown
        const addonSelect = document.getElementById('edit_add_on_plan');
        addonSelect.innerHTML = '';  // Clear previous

        data.add_on_plans.forEach(plan => {
            const option = document.createElement('option');
            option.value = plan.id;
            option.textContent = `${plan.name} - ₹${plan.price}`;
            addonSelect.appendChild(option);
        });


        // Populate form
        document.getElementById('edit_customer_id').value = customerId;
        document.getElementById('edit_name').value = data.name || '';
        document.getElementById('edit_mobile').value = data.mobile || '';
        document.getElementById('edit_email').value = data.email || '';
        document.getElementById('edit_address').value = data.address || '';
        document.getElementById('edit_base_plan').value = data.base_plan_id || '';

        // Set selected add-on options (multi-select)
        if (Array.isArray(data.addon_plan_ids)) {
            for (let option of addonSelect.options) {
                if (data.add_on_plan.includes(parseInt(option.value))) {
                    option.selected = true;
                }
            }
        }

        document.getElementById('edit_due_amount').value = data.due_amount || '';
        document.getElementById('edit_revised_amount').value = data.revised_amount || '';
        document.getElementById('edit_start_date').value = data.start_date || '';

        const modal = new bootstrap.Modal(document.getElementById('EditUser'));
        modal.show();
    } catch (err) {
        console.error('Error loading customer data:', err);
    }
}

document.addEventListener('DOMContentLoaded', function () {
    // Handle form submission
    document.getElementById('editCustomerForm').addEventListener('submit', async function(event) {
        event.preventDefault();
        console.log("JS is intercepting the update form");
        console.log("JS is handling the form");  // <-- Debug check

        const customerId = document.getElementById('edit_customer_id').value;
        console.log("Updating customer ID:", customerId);

        const formData = new FormData(this);

        try {
            const response = await fetch(`/dashboard/customer/edit/${customerId}/`, {
                method: 'POST',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                },
                body: formData
            });

            const result = await response.json();

            if (result.success) {
                alert(result.message);
                window.location.reload();
            } else {
                alert("Error: " + JSON.stringify(result.errors));
            }
        } catch (error) {
            console.error('Update failed:', error);
        }
    });
});
// Optional: Reset form on close
document.getElementById('EditUser').addEventListener('hidden.bs.modal', function () {
    document.getElementById('editCustomerForm').reset();
    currentCustomerId = null;
});

