function setupScrollingText(containerId, textId) {
  const textContainer = document.getElementById(containerId);
  const text = document.getElementById(textId);
  let isAnimating = true; // Flag to control the animation loop

  function calculateDuration() {
    const textWidth = text.offsetWidth;
    const containerWidth = textContainer.offsetWidth;
    return (textWidth / containerWidth) * 5; // Adjust this for speed
  }

  function scrollText() {
    if (!isAnimating) return; // Exit if animation was stopped
    if (text.offsetWidth < textContainer.offsetWidth) return;
    const scrollingDuration = calculateDuration();
    text.style.transition = `left ${scrollingDuration}s linear`;
    text.style.left = `-${text.offsetWidth - textContainer.offsetWidth}px`;

    setTimeout(() => {
      if (!isAnimating) return; // Check again before fading out

      text.style.opacity = "0";
      setTimeout(() => {
        if (!isAnimating) return; // Check again before resetting

        text.style.transition = "none"; // Disable transition for instant reset
        text.style.left = "0";
        text.style.opacity = "1";

        setTimeout(() => {
          if (!isAnimating) return; // Check again before restarting
          text.style.transition = `left ${scrollingDuration}s linear`; // Re-enable transition
          scrollText(); // Restart the animation
        }, 1000); // Short delay before restarting
      }, 2000); // Time before restarting the animation
    }, scrollingDuration * 1000); // Convert seconds to milliseconds
  }

  function updateText(newText) {
    isAnimating = false; // Stop current animation
    text.textContent = newText;

    setTimeout(() => {
      isAnimating = true; // Resume animation
      scrollText(); // Restart with new text
    }, 3000); // Short delay to apply new text and dimensions
  }

  function start() {
    isAnimating = true;
    scrollText();
  }

  function stop() {
    isAnimating = false;
  }

  // Start the animation initially
  start();

  // Return control methods for each instance
  return {
    updateText,
    start,
    stop,
  };
}
