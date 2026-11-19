document.addEventListener('DOMContentLoaded', function () {
  const nameField = document.getElementById('staff-name');
  const roleField = document.getElementById('staff-role-select');
  const emailField = document.getElementById('staff-email');
  const emailRequired = document.getElementById('staff-email-required');
  const emailHint = document.getElementById('staff-email-hint');
  const previewAvatar = document.getElementById('staff-preview-avatar');
  const previewName = document.getElementById('staff-preview-name');
  const previewRole = document.getElementById('staff-preview-role');
  const statusField = document.getElementById('staff-status-select');
  const previewStatus = document.getElementById('staff-preview-status');

  function initials(name) {
    return name.trim().split(/\s+/).filter(Boolean).slice(0, 2).map(function (part) { return part[0]; }).join('').toUpperCase() || 'ST';
  }

  function updateName() {
    const name = nameField.value.trim();
    previewName.textContent = name || 'New team member';
    previewAvatar.textContent = initials(name);
  }

  nameField.addEventListener('input', updateName);
  updateName();
  function updateRole() {
    const isManager = roleField.value.toLowerCase() === 'manager';
    previewRole.textContent = roleField.value || 'Select a role';
    emailField.required = isManager;
    emailRequired.hidden = !isManager;
    emailHint.textContent = isManager
      ? 'A verification email will be sent before manager sign-in details are issued.'
      : 'Optional contact email for this staff member.';
  }

  function updateStatus() {
    previewStatus.querySelector('span').textContent = statusField.value;
    previewStatus.classList.toggle('is-inactive', statusField.value === 'Inactive');
  }

  roleField.addEventListener('change', updateRole);
  updateRole();
  statusField.addEventListener('change', updateStatus);
  updateStatus();
});
