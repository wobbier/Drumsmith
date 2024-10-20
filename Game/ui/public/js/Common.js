function toggleFlyout(flyout, otherMenu) {
  const menu = document.getElementById(flyout);

  if (menu.classList.contains("active")) {
    menu.classList.remove("active");
  } else {
    menu.classList.add("active");
  }
}
