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

  /* ---------- NO PAST DATE  ---------- */
  const today = new Date().toISOString().split("T")[0];
  const startDateInput = document.getElementById("start_date");
  const editStartDateInput = document.getElementById("edit_start_date");

  if (startDateInput) {
    startDateInput.setAttribute("min", today);
  }

  if (editStartDateInput) {
    editStartDateInput.setAttribute("min", today);
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
          // Clear existing field errors
          form.querySelectorAll('.field-error').forEach(el => el.remove());

          const alertBox = form.querySelector('.planErrorAlert');
          const alertMessage = form.querySelector('.planErrorMessage');

          let msg = result.message || result.errors || 'Something went wrong';

          if (typeof msg === 'object' && msg !== null) {
            const messages = [];

            for (const [field, errors] of Object.entries(msg)) {
              const inputField = form.querySelector(`[name="${field}"]`);
              if (inputField && Array.isArray(errors)) {
                const errorDiv = document.createElement('div');
                errorDiv.className = 'text-danger mt-1 small field-error';
                errorDiv.textContent = errors[0];
                inputField.insertAdjacentElement('afterend', errorDiv);
              }

              if (Array.isArray(errors)) {
                messages.push(errors[0]);
              } else {
                messages.push(errors);
              }
            }

            if (alertBox && alertMessage) {
              alertMessage.textContent = messages.join('\n');
              alertBox.classList.remove('d-none');
            }
          } else {
            if (alertBox && alertMessage) {
              alertMessage.textContent = msg;
              alertBox.classList.remove('d-none');
            }
          }
        }
      } catch (err) {
        console.error("Plan form submission error:", err);
      }
    });
  });

  /* ---------- RESET CREATE CUSTOMER FORM ON MODAL CLOSE ---------- */
  const createCustomerModal = document.getElementById('createUser');
  const createCustomerForm = createCustomerModal?.querySelector('form');

  if (createCustomerModal && createCustomerForm) {
    createCustomerModal.addEventListener('hidden.bs.modal', function () {
      createCustomerForm.reset();

      // Remove validation errors
      createCustomerForm.querySelectorAll('.text-danger').forEach(el => el.remove());

      // Optionally reset Select2 if used
      const addOnPlanSelect = createCustomerForm.querySelector('#id_add_on_plan');
      if (addOnPlanSelect) {
        $(addOnPlanSelect).val(null).trigger('change');
      }
    });
  }

  /* ---------- RESET EDIT CUSTOMER FORM ON MODAL CLOSE ---------- */
  const editCustomerModal = document.getElementById('editUser');
  const editCustomerForm = editCustomerModal?.querySelector('form');

  if (editCustomerModal && editCustomerForm) {
    editCustomerModal.addEventListener('hidden.bs.modal', function () {
      // Reset the form fields
      editCustomerForm.reset();

      // Remove validation errors
      editCustomerForm.querySelectorAll('.text-danger').forEach(el => el.remove());

      // Get Select2 elements
      const basePlanSelect = editCustomerForm.querySelector('#id_base_plan');
      const addOnPlanSelect = editCustomerForm.querySelector('#id_add_on_plan');

      // Reset both only if both are present
      if (basePlanSelect && addOnPlanSelect) {
        $(basePlanSelect).val(null).trigger('change');
        $(addOnPlanSelect).val(null).trigger('change');
      }
    });
  }


  /* ---------- RESET PLAN FORM ON MODAL CLOSE ---------- */
  const planModal = document.getElementById('createplan');
  const planForm = planModal?.querySelector('form');

  if (planModal && planForm) {
    planModal.addEventListener('hidden.bs.modal', function () {
      planForm.reset();

      planForm.querySelectorAll('.text-danger').forEach(el => el.remove());
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
      e.preventDefault();

      const isValid = await validateCustomerCreateForm(this);
      if (!isValid) return;

      // proceed with submission
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
          const modal = bootstrap.Modal.getInstance(document.getElementById('createUser'));
          if (modal) modal.hide();

          this.reset();
          const msgEl = document.getElementById('successMessage');
          if (msgEl) {
            msgEl.textContent = "Customer Created Successfully";
          }

          const successModal = new bootstrap.Modal(document.getElementById('successModal'));
          successModal.show();

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

  /* ---------- EDIT CUSTOMER MODAL ---------- */
  $('#editUser').on('shown.bs.modal', function () {
    const $modal = $('#editUser');
    const $baseSel = $modal.find('#edit_base_plan');
    const $addSel = $modal.find('#edit_add_on_plan');
    const $dueAmt = $modal.find('#edit_due_amount');
    const $revisedAmt = $modal.find('#edit_revised_amount');

    // Initialize Select2 for Add-on Plan
    $addSel.select2({
      dropdownParent: $modal,
      placeholder: 'Select Add‑on Plans',
      width: 'resolve',
      allowClear: true,
    });

    // Refresh plan info
    function refreshEditPlanInfo() {
      const baseId = $baseSel.val() || '';
      const addonIds = $addSel.val() ? $addSel.val().join(',') : '';

      if (!baseId) {
        $dueAmt.val('');
        $revisedAmt.val('');
        return;
      }

      fetch(`/dashboard/customers/plan-info/?base_plan=${baseId}&add_on_plan=${addonIds}`)
        .then(response => response.json())
        .then(data => {
          const due = parseFloat(data.due_amount || 0);
          $dueAmt.val(due.toFixed(2));

          // Only set revised if it's currently empty (so we don't overwrite server/user provided value)
          const revisedVal = ($revisedAmt.val() || '').toString().trim();
          if (!revisedVal) {
            $revisedAmt.val(due.toFixed(2));
          }
        })
        .catch(err => {
          console.error('Error fetching plan info for edit modal:', err);
        });
    }

    // Bind change events (use namespaced handlers and remove previous handlers to avoid duplicates)
    $baseSel.off('.editPlan').on('change.editPlan', refreshEditPlanInfo);
    $addSel.off('.editPlan').on('change.editPlan select2:select.editPlan select2:unselect.editPlan', refreshEditPlanInfo);;
  });


  /* ---------- SELECT2 INIT FOR EDIT MODAL ---------- */
  $('#editUser').on('shown.bs.modal', function () {
    $('#edit_add_on_plan').select2({
      dropdownParent: $('#editUser'),
      placeholder: 'edit Add-on Plans',
      width: 'resolve',
      allowClear: true,
    });
  });

  /* ---------- DELETE CONFIRMATION ---------- */
  const deleteModal = new bootstrap.Modal(document.getElementById("DeactivateModal"));
  const confirmBtn = document.getElementById("DelmodalConfirmBtn");
  let formToSubmit = null;

  document.addEventListener("submit", function (e) {
    if (e.target && e.target.classList.contains("deleteForm")) {
      e.preventDefault();
      formToSubmit = e.target;

      const customerName = formToSubmit.querySelector("button").getAttribute("data-name");
      const icon = formToSubmit.querySelector("i");

      const modalTitle = document.getElementById("modalTitle");
      const modalActionText = document.getElementById("modalActionText");
      const modalIcon = document.getElementById("modalIcon");
      const modalIconWrapper = document.getElementById("modalIconWrapper");

      // Set customer name
      document.getElementById("deactivateCustomerName").textContent = customerName;

      if (icon.classList.contains("fa-user-xmark")) {
        // Deactivate mode
        modalTitle.textContent = "Deactivating User?";
        modalTitle.className = "text-danger";
        modalActionText.textContent = "Deactivate";
        confirmBtn.textContent = "Deactivate";
        confirmBtn.className = "btn btn-danger";
        modalIcon.className = "fa-solid fa-user-xmark";
        modalIconWrapper.className = "danger-modal-round mb-3";
      } else {
        // Activate mode
        modalTitle.textContent = "Activating User?";
        modalTitle.className = "text-success";
        modalActionText.textContent = "Activate";
        confirmBtn.textContent = "Activate";
        confirmBtn.className = "btn btn-success";
        modalIcon.className = "fa-solid fa-user-check";
        modalIconWrapper.className = "success-modal-round mb-3";
      }

      deleteModal.show();
    }
  });

  confirmBtn.addEventListener("click", function () {
    if (formToSubmit) {
      formToSubmit.submit();
      formToSubmit = null;
    }
  });



  // Confirm delete
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

      const isValid = await validateCustomerCreateForm(this, true);
      if (!isValid) return;


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
          const editModalEl = document.getElementById('editUser'); // use correct ID case
          const editModalInstance = bootstrap.Modal.getInstance(editModalEl);

          if (editModalInstance) {
            // Attach event to run AFTER modal is fully hidden
            editModalEl.addEventListener('hidden.bs.modal', function handler() {
              // Remove this event listener after it runs once
              editModalEl.removeEventListener('hidden.bs.modal', handler);

              // Reset the form
              editForm.reset();

              // Set success message
              const msgEl = document.getElementById('successMessage');
              if (msgEl) msgEl.textContent = "Customer Updated Successfully";

              // Show success modal
              const successModal = new bootstrap.Modal(document.getElementById('successModal'));
              successModal.show();

              // Reload on OK click
              document.querySelector('#successModal .okbtn').addEventListener('click', () => {
                window.location.reload();
              }, { once: true });
            });

            // Now hide the edit modal
            editModalInstance.hide();
          }
        }
        else {
          const alertBox = document.getElementById('editErrorAlert');
          const alertMessage = document.getElementById('editErrorMessage');

          // Clear existing field errors
          document.querySelectorAll('.field-error').forEach(el => el.remove());

          let msg = result.message || result.errors || 'Something went wrong';

          if (typeof msg === 'object' && msg !== null) {
            const messages = [];

            for (const [field, errors] of Object.entries(msg)) {
              const inputField = document.getElementById(`edit_${field}`);
              if (inputField && Array.isArray(errors)) {
                // Display inline error below field
                const errorDiv = document.createElement('div');
                errorDiv.className = 'text-danger mt-1 small field-error';
                errorDiv.textContent = errors[0];
                inputField.insertAdjacentElement('afterend', errorDiv);
              }

              // Collect messages for alert box
              if (Array.isArray(errors)) {
                messages.push(errors[0]);
              } else {
                messages.push(errors);
              }
            }

            if (alertBox && alertMessage) {
              alertMessage.textContent = messages.join('\n');
              alertBox.classList.remove('d-none');
            }
          } else {
            // Handle plain string error
            if (alertBox && alertMessage) {
              alertMessage.textContent = msg;
              alertBox.classList.remove('d-none');
            }
          }
        }

      } catch (error) {
        console.error('Update failed:', error);
      }
    });

    const editModal = document.getElementById('editUser');
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
    $(addonSelect).trigger('change'); // so Select2 syncs with selected options

    // Keep backend values, don't overwrite them
    document.getElementById('edit_due_amount').value = data.due_amount || '';
    document.getElementById('edit_revised_amount').value = data.revised_amount || '';

    // Start date handling
    const startDateInput = document.getElementById('edit_start_date');
    const startDateStr = data.start_date || '';
    startDateInput.value = startDateStr;

    if (startDateStr) {
      const subscriptionStartDate = new Date(startDateStr);
      const today = new Date();
      today.setHours(0, 0, 0, 0);

      if (subscriptionStartDate <= today) {
        startDateInput.readOnly = true;
        startDateInput.classList.add('bg-light');
        startDateInput.title = 'Start date cannot be edited after subscription begins.';
      } else {
        startDateInput.readOnly = false;
        startDateInput.classList.remove('bg-light');
        startDateInput.removeAttribute('title');
      }
    }

    const modalElement = document.getElementById('editUser');
    const modal = bootstrap.Modal.getOrCreateInstance(modalElement);
    modal.show();
  } catch (err) {
    console.error('Error loading customer data:', err);
  }
}


/* ---------- VALIDATION HELPERS ---------- */
async function validateCustomerCreateForm(form, isEdit = false) {
  let isValid = true;
  form.querySelectorAll('.text-danger').forEach(el => el.remove());

  const nameField = form.querySelector('[name="name"]');
  const nameValue = nameField?.value.trim();
  const addressField = form.querySelector('[name="address"]');
  const mobileField = form.querySelector('[name="mobile"]');
  const mobileValue = mobileField?.value.trim();
  const emailField = form.querySelector('[name="email"]');
  const emailValue = emailField?.value.trim();
  const basePlan = form.querySelector('[name="base_plan"]');
  const addOnPlan = form.querySelector('[name="add_on_plan"]');
  const startDateField = form.querySelector('[name="start_date"]');

  if (!nameValue) {
    showError(nameField, "Customer name is required");
    isValid = false;
  } else if (!/^[a-zA-Z\s]{3,50}$/.test(nameValue)) {
    showError(nameField, "Name must be 3-50 letters only (no numbers or special characters)");
    isValid = false;
  }

  if (!addressField?.value.trim()) {
    showError(addressField, "Address is required");
    isValid = false;
  }

  if (!mobileValue) {
    showError(mobileField, "Mobile number is required");
    isValid = false;
  } else if (!/^\d{10}$/.test(mobileValue)) {
    showError(mobileField, "Mobile number must be exactly 10 digits");
    isValid = false;
  }

  const lowercaseEmailRegex = /^[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}$/;
  if (!emailValue) {
    showError(emailField, "Email is required");
    isValid = false;
  } else if (!lowercaseEmailRegex.test(emailValue)) {
    showError(emailField, "Email must be in lowercase and valid format (e.g., example@domain.com)");
    isValid = false;
  }

  const baseSelected = basePlan && basePlan.value.trim() !== "";
  const addonSelected = addOnPlan && Array.from(addOnPlan.selectedOptions).length > 0;

  if (!baseSelected) {
    // Base plan must be selected
    showError(basePlan, "Please select a base plan.");
    isValid = false;
  }

  if (addonSelected && !baseSelected) {
    // Add-on selected without base plan
    showError(addOnPlan, "You must select a base plan before choosing add-ons.");
    isValid = false;
  }


  if (!startDateField?.value.trim()) {
    showError(startDateField, "Start date is required");
    isValid = false;
  }

  // 🔍 Skip duplicate check if editing
  if (!isEdit && isValid) {
    try {
      const response = await fetch("/dashboard/customers/check-duplicates/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCSRFToken(),
        },
        body: JSON.stringify({ name: nameValue, email: emailValue, mobile: mobileValue }),
      });

      const data = await response.json();

      if (data.name_exists) {
        showError(nameField, "Customer name already exists");
        isValid = false;
      }
      if (data.email_exists) {
        showError(emailField, "Email already exists");
        isValid = false;
      }
      if (data.mobile_exists) {
        showError(mobileField, "Mobile number already exists");
        isValid = false;
      }

    } catch (err) {
      console.error("Error checking duplicates:", err);
    }
  }

  return isValid;
}


function getCSRFToken() {
  const name = "csrftoken";
  const cookies = document.cookie.split(';');
  for (let cookie of cookies) {
    let [key, value] = cookie.trim().split('=');
    if (key === name) return decodeURIComponent(value);
  }
  return "";
}

function validatePlanForm(form) {
  let isValid = true;
  form.querySelectorAll('.text-danger').forEach(el => el.remove());

  const requiredFields = [
    {
      name: "name",
      message: "Plan name is required",
      regex: /^.{3,50}$/,
      regexMessage: "Plan name must be 3-50 characters"
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
