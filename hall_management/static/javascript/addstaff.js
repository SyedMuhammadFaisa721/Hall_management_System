document.addEventListener('DOMContentLoaded', function () {
  const nameField = document.getElementById('staff-name');
  const roleField = document.getElementById('staff-role-select');
  const avatarField = document.getElementById('staff-avatar');
  const avatarPreview = document.getElementById('staff-avatar-preview');
  const previewAvatar = document.getElementById('staff-preview-avatar');
  const previewName = document.getElementById('staff-preview-name');
  const previewRole = document.getElementById('staff-preview-role');
  const feedback = document.getElementById('staff-form-feedback');

  function initials(name) {
    return name.trim().split(/\s+/).filter(Boolean).slice(0, 2).map(function (part) { return part[0]; }).join('').toUpperCase() || 'ST';
  }

  nameField.addEventListener('input', function () {
    const name = nameField.value.trim();
    previewName.textContent = name || 'New team member';
    if (!previewAvatar.querySelector('img')) previewAvatar.textContent = initials(name);
    if (!avatarPreview.querySelector('img')) avatarPreview.textContent = initials(name);
  });
  roleField.addEventListener('change', function () { previewRole.textContent = roleField.value; });
  avatarField.addEventListener('change', function () {
    const file = avatarField.files && avatarField.files[0];
    if (!file || !file.type.startsWith('image/')) return;
    const imageUrl = URL.createObjectURL(file);
    [avatarPreview, previewAvatar].forEach(function (target) {
      const image = document.createElement('img');
      image.src = imageUrl;
      image.alt = '';
      target.replaceChildren(image);
    });
  });
  document.getElementById('add-staff-form').addEventListener('submit', function (event) {
    event.preventDefault();
    if (!event.currentTarget.reportValidity()) return;
    feedback.textContent = 'Preview only: connect a backend to save this staff member.';
  });
});
