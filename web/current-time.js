/* Shared current-time action for date/time forms. */
(function () {
  function pad(value) { return String(value).padStart(2, '0'); }

  function setCurrentTime(button) {
    const now = new Date();
    const yearInput = document.querySelector(button.dataset.yearInput);
    if (yearInput) {
      const fields = {
        year: yearInput,
        month: document.querySelector(button.dataset.monthInput),
        day: document.querySelector(button.dataset.dayInput),
        hour: document.querySelector(button.dataset.hourInput),
        minute: document.querySelector(button.dataset.minuteInput),
      };
      const solarRadio = document.querySelector(button.dataset.solarRadio || 'input[name="calendar"][value="solar"]');
      if (solarRadio && !solarRadio.checked) {
        solarRadio.checked = true;
        solarRadio.dispatchEvent(new Event('change', { bubbles: true }));
      }
      if (fields.year) fields.year.value = now.getFullYear();
      if (fields.month) fields.month.value = now.getMonth() + 1;
      if (fields.day) fields.day.value = now.getDate();
      if (fields.hour) fields.hour.value = now.getHours();
      if (fields.minute) fields.minute.value = now.getMinutes();
      Object.values(fields).filter(Boolean).forEach(input => input.dispatchEvent(new Event('change', { bubbles: true })));
      button.dataset.updatedAt = now.toISOString();
      return;
    }
    const dateInput = document.querySelector(button.dataset.dateInput);
    const timeInput = document.querySelector(button.dataset.timeInput);
    if (!dateInput || !timeInput) return;

    const solarRadio = document.querySelector(button.dataset.solarRadio || 'input[name="calendar"][value="solar"]');
    if (solarRadio && !solarRadio.checked) {
      solarRadio.checked = true;
      solarRadio.dispatchEvent(new Event('change', { bubbles: true }));
    }

    dateInput.value = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
    const seconds = timeInput.step === '1' ? `:${pad(now.getSeconds())}` : '';
    timeInput.value = `${pad(now.getHours())}:${pad(now.getMinutes())}${seconds}`;
    dateInput.dispatchEvent(new Event('change', { bubbles: true }));
    timeInput.dispatchEvent(new Event('change', { bubbles: true }));
    button.dataset.updatedAt = now.toISOString();
  }

  function mount() {
    document.querySelectorAll('[data-current-time]').forEach(button => {
      button.addEventListener('click', () => setCurrentTime(button));
    });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mount);
  else mount();
})();
