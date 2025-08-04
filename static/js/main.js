document.addEventListener("DOMContentLoaded", function () {
  /* ---------- DATATABLES ---------- */
  [
    "#myTable",
    "#PaymentHistoryTable",
    "#CustomerListTable",
    "#RecentPaymentTable",
    "#PaymentManagementTable",
  ].forEach(id => {
    const el = document.querySelector(id);
    if (el) {
      new DataTable(id, {
        responsive: true,
        searching: false,
        lengthChange: false,
      });
    }
  });

  /* ---------- PASSWORD TOGGLE ---------- */
  const toggle = document.getElementById("togglePassword");
  const passwordField = document.getElementById("id_password");
  if (toggle && passwordField) {
    toggle.addEventListener("click", function () {
      const type = passwordField.getAttribute("type") === "password" ? "text" : "password";
      passwordField.setAttribute("type", type);
      this.classList.toggle("fa-eye");
      this.classList.toggle("fa-eye-slash");
    });
  }

  /* ---------- PLAN FORM VALIDATION ---------- */
  document.querySelectorAll('.plan-form').forEach(form => {
    form.addEventListener('submit', function (e) {
      if (!validatePlanForm(form)) e.preventDefault();
    });
  });

  /* ---------- CREATE CUSTOMER MODAL ---------- */
  $('#createUser').on('shown.bs.modal', function () {
    const $modal   = $('#createUser');
    const $baseSel = $modal.find('#id_base_plan');
    const $addSel  = $modal.find('#id_add_on_plan');
    const $dueAmt  = $modal.find('#due_amount');

    $addSel.select2({
      dropdownParent: $modal,
      placeholder: 'Select Add‑on Plans',
      width: 'resolve',
      allowClear: true,
    });

    function refreshPlanInfo () {
      const baseId   = $baseSel.val() || '';
      const addonIds = $addSel.val() ? $addSel.val().join(',') : '';

      if (!baseId) return $dueAmt.val('');

      fetch(`/dashboard/customers/plan-info/?base_plan=${baseId}&add_on_plan=${addonIds}`)
        .then(r => r.json())
        .then(data => $dueAmt.val(data.due_amount || ''))
        .catch(err => console.error('plan‑info error', err));
    }

    $baseSel.on('change', refreshPlanInfo);
    $addSel.on('change select2:select select2:unselect', refreshPlanInfo);
    refreshPlanInfo();
  });

  /* ---------- CREATE CUSTOMER FORM VALIDATION ---------- */
  const createForm = document.getElementById('createCustomerForm');
  if (createForm) {
    createForm.addEventListener('submit', function (e) {
      if (!validateCustomerCreateForm(this)) {
        e.preventDefault();
      }
    });
  }

  /* ---------- SELECT2 INIT FOR EDIT MODAL ---------- */
  $('#EditUser').on('shown.bs.modal', function () {
    $('#edit_add_on_plan').select2({
      dropdownParent: $('#EditUser'),
      placeholder: 'Edit Add-on Plans',
      width: 'resolve',
      allowClear: true,
    });
  });

  /* ---------- DELETE CONFIRMATION ---------- */
  const deleteModal = new bootstrap.Modal(document.getElementById("DeactivateModal"));
  const confirmBtn = document.getElementById("DelmodalConfirmBtn");
  let formToSubmit = null;

  document.querySelectorAll(".deleteForm").forEach(form => {
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      formToSubmit = form;
      deleteModal.show();
    });
  });

  confirmBtn.addEventListener("click", function () {
    if (formToSubmit) {
      formToSubmit.submit();
      formToSubmit = null;
    }
  });

  /* ---------- EDIT CUSTOMER FORM SUBMIT ---------- */
  const editForm = document.getElementById('editCustomerForm');
  if (editForm) {
    editForm.addEventListener('submit', async function (event) {
      event.preventDefault();

      if (!validateCustomerCreateForm(this)) return;

      const customerId = document.getElementById('edit_customer_id').value;
      const formData = new FormData(this);

      try {
        const response = await fetch(`/dashboard/customer/edit/${customerId}/`, {
          method: 'POST',
          headers: { 'X-Requested-With': 'XMLHttpRequest' },
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

    const editModal = document.getElementById('EditUser');
    if (editModal) {
      editModal.addEventListener('hidden.bs.modal', function () {
        editForm.reset();
      });
    }
  }
});

/* ---------- LOAD CUSTOMER DATA FOR EDIT ---------- */
async function loadCustomerData(customerId) {
  try {
    const response = await fetch(`/dashboard/customer/edit/${customerId}/`, {
      method: 'GET',
      headers: { 'X-Requested-With': 'XMLHttpRequest' }
    });

    if (!response.ok) throw new Error('Fetch failed');

    const data = await response.json();
    const baseSelect = document.getElementById('edit_base_plan');
    const addonSelect = document.getElementById('edit_add_on_plan');

    baseSelect.innerHTML = '<option value="">Select Base Plan</option>';
    data.base_plans.forEach(plan => {
      baseSelect.insertAdjacentHTML('beforeend', `<option value="${plan.id}">${plan.name} - ₹${plan.price}</option>`);
    });

    addonSelect.innerHTML = '';
    data.add_on_plans.forEach(plan => {
      addonSelect.insertAdjacentHTML('beforeend', `<option value="${plan.id}">${plan.name} - ₹${plan.price}</option>`);
    });

    document.getElementById('edit_customer_id').value = customerId;
    document.getElementById('edit_name').value = data.name || '';
    document.getElementById('edit_mobile').value = data.mobile || '';
    document.getElementById('edit_email').value = data.email || '';
    document.getElementById('edit_address').value = data.address || '';
    document.getElementById('edit_base_plan').value = data.base_plan_id || '';

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

/* ---------- VALIDATION HELPERS ---------- */
function validateCustomerCreateForm(form) {
  let isValid = true;
  form.querySelectorAll('.text-danger').forEach(el => el.remove());

  const requiredFields = [
    { name: "name", message: "Customer name is required" },
    { name: "address", message: "Address is required" }
  ];

  requiredFields.forEach(({ name, message }) => {
    const field = form.querySelector(`[name="${name}"]`);
    if (!field || !field.value.trim()) {
      showError(field, message);
      isValid = false;
    }
  });

  const mobileField = form.querySelector('[name="mobile"]');
  const mobileValue = mobileField?.value.trim();
  if (!mobileValue) {
    showError(mobileField, "Mobile number is required");
    isValid = false;
  } else if (!/^\d{10}$/.test(mobileValue)) {
    showError(mobileField, "Mobile number must be exactly 10 digits");
    isValid = false;
  }

  const emailField = form.querySelector('[name="email"]');
  const emailValue = emailField?.value.trim();
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  if (!emailValue) {
    showError(emailField, "Email is required");
    isValid = false;
  } else if (!emailRegex.test(emailValue)) {
    showError(emailField, "Enter a valid email address");
    isValid = false;
  }

  const basePlan = form.querySelector('[name="base_plan"]');
  const addOnPlan = form.querySelector('[name="add_on_plan"]');
  const baseSelected = basePlan && basePlan.value.trim() !== "";
  const addonSelected = addOnPlan && Array.from(addOnPlan.selectedOptions).length > 0;

  if (!baseSelected && !addonSelected) {
    showError(basePlan, "Select at least one plan.");
    showError(addOnPlan, "Select at least one plan.");
    isValid = false;
  }

  if (baseSelected && addonSelected) {
    showError(basePlan, "Choose only one: base plan or add-on plans.");
    showError(addOnPlan, "Choose only one: base plan or add-on plans.");
    isValid = false;
  }

  return isValid;
}

function validatePlanForm(form) {
  let isValid = true;
  form.querySelectorAll('.text-danger').forEach(el => el.remove());

  const requiredFields = [
    { name: "name", message: "Plan name is required" },
    { name: "plan_type", message: "Plan type is required" },
    { name: "price", message: "Enter a valid price (0 or more)", numeric: true, min: 0 },
    { name: "duration_days", message: "Duration must be at least 1 day", numeric: true, min: 1 },
    { name: "description", message: "Description is required" }
  ];

  requiredFields.forEach(({ name, message, numeric, min }) => {
    const field = form.querySelector(`[name="${name}"]`);
    if (!field) return;

    const value = field.value.trim();
    if (!value || (numeric && (isNaN(value) || Number(value) < min))) {
      showError(field, message);
      isValid = false;
    }
  });

  return isValid;
}

function showError(input, message) {
  const error = document.createElement('div');
  error.className = 'text-danger small mt-1';
  error.textContent = message;
  input?.parentNode?.appendChild(error);
}
