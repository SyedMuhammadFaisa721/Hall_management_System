(() => {
  const themeButtons = document.querySelectorAll("[data-theme-choice]");
  const themeColor = document.querySelector('meta[name="theme-color"]');

  function applyTheme(theme) {
    document.documentElement.setAttribute("data-theme", theme);
    themeButtons.forEach((button) => {
      const selected = button.dataset.themeChoice === theme;
      button.setAttribute("aria-pressed", String(selected));
      button.setAttribute(
        "aria-label",
        `Switch to ${button.dataset.themeChoice === "light" ? "day" : "night"} theme`
      );
    });

    if (themeColor) {
      themeColor.setAttribute("content", theme === "light" ? "#F7F4ED" : "#07090b");
    }

    window.dispatchEvent(new CustomEvent("hallmaster:themechange", { detail: { theme } }));
  }

  const initialTheme =
    document.documentElement.getAttribute("data-theme") === "light" ? "light" : "dark";
  applyTheme(initialTheme);

  themeButtons.forEach((button) => {
    button.addEventListener("click", () => {
      const theme = button.dataset.themeChoice;
      if (theme !== "light" && theme !== "dark") return;

      applyTheme(theme);
      try {
        localStorage.setItem("hallmaster-theme", theme);
      } catch (error) {
        console.error("Unable to save the HallMaster theme preference.", error);
      }
    });
  });
})();
