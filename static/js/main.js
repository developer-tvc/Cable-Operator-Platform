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

  /* ---------- BLOCK INVALID NUMBER INPUT (PRICE & DURATION) ---------- */
  function blockInvalidInput(e, min) {
    const input = e.target;
    const futureValue = input.value + e.key;

    // Allow essential keys
    if (
      ["Backspace", "Delete", "ArrowLeft", "ArrowRight", "Tab"].includes(e.key) ||
      e.ctrlKey || e.metaKey
    ) return;

    const numericValue = parseInt(futureValue);

    if (JSON.stringify(numericValue).length === JSON.stringify(min).length) {
      if (!/^\d$/.test(e.key)) {
        e.preventDefault();
        return;
      }

      if (!isNaN(numericValue) && numericValue < min) {
        e.preventDefault();
      }
    }
  }

  /* ---------- FOCUSOUT VALIDATION (Fallback for typing/pasting/etc) ---------- */
  function validateOnBlur(input, min) {
    const val = parseInt(input.value.trim());
    if (isNaN(val) || val < min) {
      input.value = "";
    }
  }

  /* ---------- PLAN FORM SUBMISSION ---------- */
  document.querySelectorAll('.plan-form').forEach(form => {
    const priceInput = form.querySelector('[name="price"]');
    const durationInput = form.querySelector('[name="duration_days"]');

    if (priceInput) {
      priceInput.addEventListener('keypress', function (e) {
        blockInvalidInput(e, 1);
      });
      priceInput.addEventListener('focusout', function () {
        validateOnBlur(priceInput, 1);
      });
    }

    if (durationInput) {
      durationInput.addEventListener('keypress', function (e) {
        blockInvalidInput(e, 30);
      });
      durationInput.addEventListener('focusout', function () {
        validateOnBlur(durationInput, 30);
      });
    }

    form.addEventListener('submit', async function (e) {
      e.preventDefault();
      if (!validatePlanForm(form)) return;

      const formData = new FormData(form);
      const actionUrl = form.getAttribute('action');
      const isEdit = actionUrl.includes('update');

      try {
        const response = await fetch(actionUrl, {
          method: 'POST',
          headers: { 'X-Requested-With': 'XMLHttpRequest' },
          body: formData,
        });

        const result = await response.json();
        if (result.success) {
          // Close modal
          const modalInstance = bootstrap.Modal.getInstance(form.closest('.modal'));
          if (modalInstance) modalInstance.hide();

          // Reset form
          form.reset();

          // Set dynamic success message
          const message = isEdit ? "Plan Updated Successfully" : "Plan Created Successfully";
          const messageElement = document.getElementById('successMessage');
          if (messageElement) {
            messageElement.textContent = message;
          }

          // Show success modal
          const successModal = new bootstrap.Modal(document.getElementById('successModal'));
          successModal.show();

          // Reload when OK button is clicked
          const okBtn = document.querySelector('#successModal .okbtn');
          if (okBtn) {
            okBtn.addEventListener('click', function () {
              window.location.reload();
            }, { once: true });  // ensure it fires only once
          }

        } else {
          alert("Error: " + JSON.stringify(result.errors));
        }
      } catch (err) {
        console.error("Plan form submission error:", err);
      }
    });
  });

  /* ---------- RESET PLAN FORM ON MODAL CLOSE ---------- */
  const planModal = document.getElementById('createplan');
  const planForm = planModal?.querySelector('form');

  if (planModal && planForm) {
    planModal.addEventListener('hidden.bs.modal', function () {
      planForm.reset();

      planForm.querySelectorAll('.text-danger').forEach(el => el.remove());
      $(planForm).find('select').val('').trigger('change');
    });
  }

  /* ---------- RESET EDIT PLAN FORM ON MODAL CLOSE ---------- */
  document.querySelectorAll('[id^="Editplan"]').forEach(modal => {
    const editForm = modal.querySelector('form');

    if (editForm) {
      modal.addEventListener('hidden.bs.modal', function () {
        editForm.reset(); // Reset form fields to default

        // Remove validation messages
        editForm.querySelectorAll('.text-danger').forEach(el => el.remove());
        
      });
    }
  });



  /* ---------- CREATE CUSTOMER MODAL ---------- */
  $('#createUser').on('shown.bs.modal', function () {
    const $modal = $('#createUser');
    const $baseSel = $modal.find('#id_base_plan');
    const $addSel = $modal.find('#id_add_on_plan');
    const $dueAmt = $modal.find('#due_amount');

    $addSel.select2({
      dropdownParent: $modal,
      placeholder: 'Select Add‑on Plans',
      width: 'resolve',
      allowClear: true,
    });

    function refreshPlanInfo() {
      const baseId = $baseSel.val() || '';
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

  /* ---------- CREATE CUSTOMER FORM SUBMISSION ---------- */
  const createForm = document.getElementById('createCustomerForm');
  if (createForm) {
    createForm.addEventListener('submit', async function (e) {
      e.preventDefault(); // prevent default form submit

      if (!validateCustomerCreateForm(this)) return;

      const formData = new FormData(this);
      const actionUrl = this.getAttribute('action');

      try {
        const response = await fetch(actionUrl, {
          method: 'POST',
          headers: {
            'X-Requested-With': 'XMLHttpRequest'
          },
          body: formData
        });

        const result = await response.json();

        if (result.success) {
          // Hide create modal
          const modal = bootstrap.Modal.getInstance(document.getElementById('createUser'));
          if (modal) modal.hide();

          // Reset form
          this.reset();

          // Set success message
          const msgEl = document.getElementById('successMessage');
          if (msgEl) {
            msgEl.textContent = "Customer Created Successfully";
          }

          // Show success modal
          const successModal = new bootstrap.Modal(document.getElementById('successModal'));
          successModal.show();

          // Reload on OK
          document.querySelector('#successModal .okbtn').addEventListener('click', function () {
            window.location.reload();
          }, { once: true });

        } else {
          alert("Error: " + JSON.stringify(result.message || result.errors));
        }

      } catch (err) {
        console.error("Customer creation failed:", err);
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
          const modal = bootstrap.Modal.getInstance(document.getElementById('EditUser'));
          if (modal) modal.hide();

          // Reset form (optional)
          this.reset();

          const msg = document.getElementById('successMessage');
          if (msg) msg.textContent = "Customer Updated Successfully";

          const successModal = new bootstrap.Modal(document.getElementById('successModal'));
          successModal.show();

          document.querySelector('#successModal .okbtn').addEventListener('click', function () {
            window.location.reload();
          }, { once: true });
        }
        else {
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
        if (data.addon_plan_ids.includes(parseInt(option.value))) {
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

  const nameField = form.querySelector('[name="name"]');
  const nameValue = nameField?.value.trim();
  if (!nameValue) {
    showError(nameField, "Customer name is required");
    isValid = false;
  } else if (!/^[a-zA-Z\s]{3,50}$/.test(nameValue)) {
    showError(nameField, "Name must be 3-50 letters only (no numbers or special characters)");
    isValid = false;
  }

  const addressField = form.querySelector('[name="address"]');
  if (!addressField?.value.trim()) {
    showError(addressField, "Address is required");
    isValid = false;
  }

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

  return isValid;
}


function validatePlanForm(form) {
  let isValid = true;
  form.querySelectorAll('.text-danger').forEach(el => el.remove());

  const requiredFields = [
    {
      name: "name",
      message: "Plan name is required",
      regex: /^[a-zA-Z0-9\s\-_.(),/&:]{3,50}$/,
      regexMessage: "Plan name must be 3-50 characters and can include letters, numbers, and special characters (- _ . , ( ) / & :)"
    },
    {
      name: "plan_type",
      message: "Plan type is required",
      isSelect: true
    },
    {
      name: "price",
      message: "Enter a valid price (1 or more)",
      numeric: true,
      min: 1
    },
    {
      name: "duration_days",
      message: "Duration must be at least 30 days",
      numeric: true,
      min: 30
    },
    {
      name: "description",
      message: "Description is required",
      minLength: 5
    }
  ];

  requiredFields.forEach(({ name, message, numeric, min, regex, regexMessage, minLength, isSelect }) => {
    const field = form.querySelector(`[name="${name}"]`);
    if (!field) return;

    const value = field.value.trim();

    if (!value) {
      showError(field, message);
      isValid = false;
      return;
    }

    if (numeric) {
      const num = Number(value);
      if (isNaN(num) || num < min) {
        showError(field, message);
        isValid = false;
        return;
      }
    }

    if (regex && !regex.test(value)) {
      showError(field, regexMessage || "Invalid format");
      isValid = false;
      return;
    }

    if (minLength && value.length < minLength) {
      showError(field, `Minimum ${minLength} characters required`);
      isValid = false;
      return;
    }

    if (isSelect && (value === "0" || value === "Select" || value === "")) {
      showError(field, message);
      isValid = false;
      return;
    }
  });

  return isValid;
}

function showError(input, message) {
  const error = document.createElement('div');
  error.className = 'text-danger small mt-1';
  error.textContent = message;

  const container = input.closest('.form-group, .input-group');
  if (container) {
    container.appendChild(error);
  } else {
    input.parentNode?.appendChild(error);
  }
}
