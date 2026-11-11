document.addEventListener("DOMContentLoaded", () => {
  const form = document.querySelector("form[data-availability-url]");
  if (!form) return;
  const veterinarian = form.querySelector("#id_veterinarian");
  const date = form.querySelector("#id_date");
  const duration = form.querySelector("#id_duration_minutes");
  const time = form.querySelector("#id_time");
  const message = form.querySelector(".availability-message");
  if (!veterinarian || !date || !duration || !time || !message) return;

  let latestRequest = 0;
  let activeController = null;
  let pendingRefresh = null;

  const refresh = async () => {
    const requestId = ++latestRequest;
    const previous = time.value;
    activeController?.abort();
    activeController = null;
    time.replaceChildren(new Option("Selecciona el profesional y la fecha", ""));
    if (!veterinarian.value || !date.value || !duration.value) {
      time.disabled = false;
      message.textContent = "";
      return;
    }

    const params = new URLSearchParams({
      veterinarian: veterinarian.value,
      date: date.value,
      duration: duration.value,
      appointment: form.dataset.appointmentId || "",
    });
    const controller = new AbortController();
    activeController = controller;
    time.disabled = true;
    message.textContent = "Buscando horarios disponibles…";
    pendingRefresh = (async () => {
      try {
        const response = await fetch(`${form.dataset.availabilityUrl}?${params}`, {
          headers: { "X-Requested-With": "XMLHttpRequest" },
          credentials: "same-origin",
          signal: controller.signal,
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || "No fue posible consultar la disponibilidad.");
        if (requestId !== latestRequest) return;
        time.replaceChildren(new Option("Selecciona una hora", ""));
        data.slots.forEach(slot => time.add(new Option(slot, slot)));
        if (data.slots.includes(previous)) time.value = previous;
        message.textContent = data.slots.length
          ? `${data.slots.length} horarios disponibles para esta jornada.`
          : "No hay horas disponibles. Prueba otra fecha o profesional.";
      } catch (error) {
        if (error.name === "AbortError" || requestId !== latestRequest) return;
        message.textContent = error.message;
      } finally {
        if (requestId === latestRequest) {
          time.disabled = false;
          activeController = null;
        }
      }
    })();
    await pendingRefresh;
  };

  veterinarian.addEventListener("change", refresh);
  date.addEventListener("change", refresh);
  duration.addEventListener("change", refresh);
  if (veterinarian.value && date.value) refresh();

  form.addEventListener("submit", async event => {
    if (!time.disabled) return;
    event.preventDefault();
    await pendingRefresh;
    if (time.value && !time.disabled) form.requestSubmit(event.submitter);
    else time.focus();
  });
});
