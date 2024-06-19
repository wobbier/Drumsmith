document.addEventListener("DOMContentLoaded", () => {
  // Create and append overlay element
  const overlay = document.createElement("div")
  overlay.id = "overlay"
  overlay.className = "overlay"
  document.body.appendChild(overlay)

  // Event listener for the overlay to close the active flyout
  overlay.addEventListener("click", () => {
    const activeFlyoutId = overlay.getAttribute("data-active-flyout")
    if (activeFlyoutId) {
      closeFlyout(activeFlyoutId)
    }
  })
})

function toggleFlyout(flyoutId) {
  const overlay = document.getElementById("overlay")
  const flyout = document.getElementById(flyoutId)
  flyout.classList.add("open")
  overlay.classList.add("show")
  overlay.setAttribute("data-active-flyout", flyoutId)
}

function openFlyout(flyoutId) {
  const overlay = document.getElementById("overlay")
  const flyout = document.getElementById(flyoutId)
  flyout.classList.add("open")
  overlay.classList.add("show")
  overlay.setAttribute("data-active-flyout", flyoutId)
}

function closeFlyout(flyoutId) {
  const overlay = document.getElementById("overlay")
  const flyout = document.getElementById(flyoutId)
  flyout.classList.remove("open")
  overlay.classList.remove("show")
  overlay.removeAttribute("data-active-flyout")
}

document.addEventListener("click", function (event) {
  const overlay = document.getElementById("overlay")
  const activeFlyoutId = overlay.getAttribute("data-active-flyout")
  const activeFlyout = document.getElementById(activeFlyoutId)
  if (
    activeFlyout &&
    !activeFlyout.contains(event.target) &&
    !event.target.classList.contains("openButton")
  ) {
    closeFlyout(activeFlyoutId)
  }
})
