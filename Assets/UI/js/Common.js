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

function applyScrollFadeAnimation(
  elementId,
  initialDelay = 1000,
  scrollAnimationTime = 5000,
  fadeOutInTime = 2000
) {
  const textElement = document.getElementById(elementId);
  if (!textElement) return; // Exit if the element does not exist

  function startAnimation() {
    const wrapperWidth = textElement.parentElement.offsetWidth;
    const textWidth = textElement.offsetWidth;
    const distanceToScroll = textWidth - wrapperWidth;

    // Step 2: Start scrolling after a delay
    setTimeout(() => {
      textElement.style.transition = `transform ${scrollAnimationTime}ms linear`;
      textElement.style.transform = `translateX(-${distanceToScroll}px)`;
    }, initialDelay); // Delay before scrolling starts

    // Step 3: Fade out after reaching the end
    setTimeout(() => {
      textElement.style.transition = `opacity ${fadeOutInTime / 2}ms linear`;
      textElement.style.opacity = "0";
    }, scrollAnimationTime + initialDelay); // After scrolling ends

    // Step 4: Reset to start position and fade in
    setTimeout(() => {
      textElement.style.transition = "none";
      textElement.style.transform = "translateX(0)";
      textElement.style.opacity = "0";

      setTimeout(() => {
        textElement.style.transition = `opacity ${fadeOutInTime / 2}ms linear`;
        textElement.style.opacity = "1";
      }, 100); // Brief pause before fading in

      // Wait for the fade in to complete before starting the next cycle
      setTimeout(startAnimation, fadeOutInTime);
    }, scrollAnimationTime + initialDelay + fadeOutInTime);
  }

  startAnimation();
}
