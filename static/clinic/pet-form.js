document.addEventListener("DOMContentLoaded", () => {
  const species = document.querySelector("#id_species");
  const detail = document.querySelector("[data-species-detail]");
  const field = detail?.closest(".form-field");
  if (!species || !detail || !field) return;
  const requiredMark = field.querySelector(".required-mark");

  const updateSpeciesField = () => {
    const showDetail = species.value === "Otro";
    field.hidden = !showDetail;
    detail.required = showDetail;
    if (requiredMark) requiredMark.hidden = !showDetail;
    if (!showDetail) detail.value = "";
    if (showDetail) field.hidden = false;
  };

  species.addEventListener("change", updateSpeciesField);
  updateSpeciesField();
});
