(function () {
  const state = new WeakMap();

  function formState(form) {
    if (!state.has(form)) {
      state.set(form, {
        availability: null,
        slotsPayload: null,
        selectedDate: "",
        selectedTime: "",
      });
    }
    return state.get(form);
  }

  async function fetchDentistAvailability(dentistId) {
    const response = await fetch(`/appointments/api/dentist-availability/${dentistId}/`, {
      headers: { "X-Requested-With": "XMLHttpRequest" },
    });
    if (!response.ok) throw new Error("Could not load dentist availability.");
    return response.json();
  }

  async function fetchAvailableSlots(dentistId, date) {
    const params = new URLSearchParams({ dentist_id: dentistId, date });
    const response = await fetch(`/appointments/api/available-slots/?${params.toString()}`, {
      headers: { "X-Requested-With": "XMLHttpRequest" },
    });
    if (!response.ok) throw new Error("Could not load time slots.");
    return response.json();
  }

  function formatDate(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, "0");
    const day = String(date.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
  }

  function setMessage(container, message, tone) {
    container.textContent = message;
    container.className = `text-sm font-medium ${tone === "error" ? "text-red-600" : "text-gray-500"}`;
  }

  function updateSubmitState(form) {
    const dentist = form.querySelector("[data-availability-dentist]");
    const date = form.querySelector("[data-availability-date]");
    const time = form.querySelector("[data-availability-time]");
    const submit = form.querySelector("[data-availability-submit]") || form.querySelector("button[type='submit']");
    if (!submit || !dentist || !date || !time) return;
    submit.disabled = !(dentist.value && date.value && time.value);
  }

  function resetBookingForm(form) {
    const data = formState(form);
    data.availability = null;
    data.selectedDate = "";
    data.selectedTime = "";
    data.slotsPayload = null;

    const date = form.querySelector("[data-availability-date]");
    const time = form.querySelector("[data-availability-time]");
    const calendar = form.querySelector("[data-availability-calendar]");
    const slots = form.querySelector("[data-availability-slots]");
    const message = form.querySelector("[data-availability-message]");
    const slotsMessage = form.querySelector("[data-availability-slots-message]");

    if (date) date.value = "";
    if (time) time.value = "";
    if (calendar) calendar.innerHTML = "";
    if (slots) slots.innerHTML = "";
    if (message) setMessage(message, "Please select a dentist to view availability.", "muted");
    if (slotsMessage) slotsMessage.textContent = "";
    updateSubmitState(form);
  }

  function renderCalendarAvailability(form) {
    const data = formState(form);
    const calendar = form.querySelector("[data-availability-calendar]");
    const message = form.querySelector("[data-availability-message]");
    if (!calendar || !data.availability) return;

    const available = new Set(data.availability.available_dates_next_60_days || []);
    const full = new Set(data.availability.fully_booked_dates || []);
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    calendar.innerHTML = "";

    if (!data.availability.is_available || available.size === 0) {
      setMessage(message, "This dentist has no availability configured.", "error");
    } else {
      setMessage(message, "Green dates are available. Red dates are fully booked.", "muted");
    }

    for (let offset = 0; offset < 60; offset += 1) {
      const date = new Date(today);
      date.setDate(today.getDate() + offset);
      const iso = formatDate(date);
      const isAvailable = available.has(iso);
      const isFull = full.has(iso);
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
      button.dataset.date = iso;
      button.className = "rounded-xl border px-3 py-2 text-xs font-bold transition";

      if (data.selectedDate === iso) {
        button.className += " border-green-600 bg-green-600 text-white";
      } else if (isAvailable) {
        button.className += " border-green-200 bg-green-50 text-green-700 hover:bg-green-100";
      } else if (isFull) {
        button.className += " cursor-not-allowed border-red-200 bg-red-50 text-red-500";
        button.disabled = true;
        button.title = "This date is fully booked.";
      } else {
        button.className += " cursor-not-allowed border-gray-200 bg-gray-100 text-gray-400";
        button.disabled = true;
        button.title = "This dentist is not available on this day.";
      }

      if (isAvailable) {
        button.addEventListener("click", function () {
          selectDate(form, iso);
        });
      }
      calendar.appendChild(button);
    }
  }

  async function selectDate(form, dateValue) {
    const dentist = form.querySelector("[data-availability-dentist]");
    const date = form.querySelector("[data-availability-date]");
    const time = form.querySelector("[data-availability-time]");
    const slots = form.querySelector("[data-availability-slots]");
    const slotsMessage = form.querySelector("[data-availability-slots-message]");
    const data = formState(form);

    data.selectedDate = dateValue;
    data.selectedTime = "";
    date.value = dateValue;
    time.value = "";
    renderCalendarAvailability(form);
    slots.innerHTML = "";
    setMessage(slotsMessage, "Loading available time slots...", "muted");
    updateSubmitState(form);

    try {
      const payload = await fetchAvailableSlots(dentist.value, dateValue);
      renderTimeSlots(form, payload);
    } catch (error) {
      setMessage(slotsMessage, error.message, "error");
    }
  }

  function renderTimeSlots(form, payload) {
    const slots = form.querySelector("[data-availability-slots]");
    const slotsMessage = form.querySelector("[data-availability-slots-message]");
    const data = formState(form);
    slots.innerHTML = "";
    data.slotsPayload = payload;

    if (payload.is_fully_booked) {
      setMessage(slotsMessage, "This date is fully booked.", "error");
      return;
    }

    if (!payload.available_slots || payload.available_slots.length === 0) {
      setMessage(slotsMessage, "No available time slots for this date.", "error");
      return;
    }

    setMessage(slotsMessage, `${payload.booked_count} of ${payload.max_patients_per_day} daily appointment spots are booked.`, "muted");
    payload.available_slots.forEach(function (slot) {
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = slot;
      button.className = "rounded-xl border border-green-200 px-3 py-2 text-sm font-bold text-green-700 transition hover:bg-green-50";
      if (data.selectedTime === slot) {
        button.className = "rounded-xl border border-green-600 bg-green-600 px-3 py-2 text-sm font-bold text-white";
      }
      button.addEventListener("click", function () {
        selectTimeSlot(form, slot);
      });
      slots.appendChild(button);
    });
  }

  function selectTimeSlot(form, slot) {
    const data = formState(form);
    const time = form.querySelector("[data-availability-time]");
    data.selectedTime = slot;
    time.value = slot;
    renderTimeSlots(form, data.slotsPayload || { available_slots: [slot], is_fully_booked: false });
    updateSubmitState(form);
  }

  function enhanceForm(form) {
    const dentist = form.querySelector("[data-availability-dentist]");
    const date = form.querySelector("[data-availability-date]");
    const time = form.querySelector("[data-availability-time]");
    if (!dentist || !date || !time || form.dataset.availabilityReady === "true") return;
    form.dataset.availabilityReady = "true";
    const initialDate = date.value;
    const initialTime = time.value ? time.value.slice(0, 5) : "";
    let restoredInitial = false;

    date.type = "hidden";
    time.type = "hidden";
    date.insertAdjacentHTML("afterend", '<div data-availability-message class="mt-2 text-sm font-medium text-gray-500">Please select a dentist to view availability.</div><div data-availability-calendar class="mt-3 grid grid-cols-3 gap-2 sm:grid-cols-5 md:grid-cols-7"></div>');
    time.insertAdjacentHTML("afterend", '<div data-availability-slots-message class="mt-2 text-sm font-medium text-gray-500"></div><div data-availability-slots class="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-4"></div>');

    dentist.addEventListener("change", async function () {
      resetBookingForm(form);
      if (!dentist.value) return;
      const message = form.querySelector("[data-availability-message]");
      setMessage(message, "Loading dentist availability...", "muted");
      try {
        formState(form).availability = await fetchDentistAvailability(dentist.value);
        renderCalendarAvailability(form);
        if (!restoredInitial && initialDate && !formState(form).selectedDate) {
          restoredInitial = true;
          await selectDate(form, initialDate);
          if (initialTime && formState(form).slotsPayload && formState(form).slotsPayload.available_slots.includes(initialTime)) {
            selectTimeSlot(form, initialTime);
          }
        }
      } catch (error) {
        setMessage(message, error.message, "error");
      }
    });

    if (dentist.value) {
      dentist.dispatchEvent(new Event("change"));
    } else {
      resetBookingForm(form);
    }
  }

  window.fetchDentistAvailability = fetchDentistAvailability;
  window.fetchAvailableSlots = fetchAvailableSlots;
  window.renderCalendarAvailability = renderCalendarAvailability;
  window.renderTimeSlots = renderTimeSlots;
  window.selectTimeSlot = selectTimeSlot;
  window.resetBookingForm = resetBookingForm;

  document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll("[data-availability-form]").forEach(enhanceForm);
  });
})();
