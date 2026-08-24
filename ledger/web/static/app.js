// Mouse-tracked 3D tilt for stat cards -- purely presentational, degrades
// gracefully to the static card if JS is disabled.
(function () {
  const MAX_TILT_DEG = 6;

  function attachTilt(card) {
    card.addEventListener("mousemove", (event) => {
      const rect = card.getBoundingClientRect();
      const px = (event.clientX - rect.left) / rect.width;
      const py = (event.clientY - rect.top) / rect.height;

      const rotateY = (px - 0.5) * MAX_TILT_DEG * 2;
      const rotateX = (0.5 - py) * MAX_TILT_DEG * 2;

      card.style.transform = `perspective(700px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) translateZ(4px)`;
      card.style.setProperty("--mx", `${px * 100}%`);
      card.style.setProperty("--my", `${py * 100}%`);
    });

    card.addEventListener("mouseleave", () => {
      card.style.transform = "";
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll(".stat-card").forEach(attachTilt);
  });
})();
