document.addEventListener("DOMContentLoaded", () => {
  const menuButton = document.querySelector("#mobile-menu");
  const sidebar = document.querySelector("#sidebar");
  if (menuButton && sidebar) {
    menuButton.addEventListener("click", () => {
      const isOpen = sidebar.classList.toggle("open");
      menuButton.setAttribute("aria-expanded", String(isOpen));
    });
    document.addEventListener("click", event => {
      if (window.innerWidth <= 820 && sidebar.classList.contains("open") &&
          !sidebar.contains(event.target) && !menuButton.contains(event.target)) {
        sidebar.classList.remove("open");
        menuButton.setAttribute("aria-expanded", "false");
      }
    });
  }

  const agendaDateForm = document.querySelector("#agenda-date-form");
  agendaDateForm?.querySelector('input[type="date"]')?.addEventListener("change", () => agendaDateForm.requestSubmit());
});
