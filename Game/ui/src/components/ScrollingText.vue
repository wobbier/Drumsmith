<template>
    <div :class="['scroll-container', containerStyle]" :id="containerId">
      <div :class="['scroll-content', textStyle]" :id="textId">{{ text }}</div>
    </div>
  </template>
  
  <script>
  export default {
    props: {
      text: {
        type: String,
        default: "Scrollable Text"
      },
      baseId: {
        type: String,
        required: true, // Base ID is required
      },
      containerStyle: {
        type: String,
        default: ""
      },
      textStyle: {
        type: String,
        default: ""
      },
    },
    data() {
      return {
        scrollingTextInstance: null,
      };
    },
    computed: {
      containerId() {
        return `${this.baseId}-container`;
      },
      textId() {
        return `${this.baseId}-text`;
      },
    },
    mounted() {
      this.scrollingTextInstance = this.setupScrollingText(this.containerId, this.textId);
    },
    watch: {
      // eslint-disable-next-line
      text(newValue, oldValue) {
        this.scrollingTextInstance.updateText(newValue);
      },
    },
    methods: {
      setupScrollingText(containerId, textId) {
        const textContainer = document.getElementById(containerId);
        const text = document.getElementById(textId);
        let isAnimating = true; // Control flag for animation
        let timeoutId; // Store timeout ID for cleanups

        // Helper to check if the text needs to scroll
        function needsScrolling() {
          return text.offsetWidth > textContainer.offsetWidth;
        }

        // Calculate scrolling duration based on text width
        function calculateDuration() {
          const textWidth = text.offsetWidth;
          const containerWidth = textContainer.offsetWidth;
          return (textWidth / containerWidth) * 5; // Adjust for desired speed
        }

        // Clear ongoing timeouts or animations
        function clearAnimations() {
          clearTimeout(timeoutId); // Clear any existing timeouts
          text.style.transition = "none"; // Stop ongoing transitions
          text.style.left = "0"; // Reset text position
          text.style.opacity = "1"; // Ensure text is visible
        }

        // Core function to handle scrolling animation
        function scrollText() {
          clearAnimations(); // Ensure any ongoing animations are cleared

          if (!isAnimating || !needsScrolling()) return;

          const scrollingDuration = calculateDuration();

          // Initial delay before scrolling starts
          timeoutId = setTimeout(() => {
            text.style.transition = `left ${scrollingDuration}s linear`;
            text.style.left = `-${text.offsetWidth - textContainer.offsetWidth}px`;

            // Once the scrolling finishes, fade out the text
            timeoutId = setTimeout(() => {
              text.style.transition = "opacity 1s ease";
              text.style.opacity = "0";

              // Once faded out, reset the position and fade back in
              timeoutId = setTimeout(() => {
                text.style.transition = "none"; // Reset transition
                text.style.left = "0"; // Reset text position
                text.style.opacity = "1"; // Fade back in

                // After fading in, restart the animation loop
                timeoutId = setTimeout(() => {
                  if (isAnimating) {
                    text.style.transition = `left ${scrollingDuration}s linear`; // Re-enable scrolling transition
                    scrollText(); // Restart the loop
                  }
                }, 1000); // Small delay before restarting
              }, 1000); // Delay before fading back in
            }, (scrollingDuration + 1) * 1000); // Wait for scrolling to finish and then fade out
          }, 1000); // Initial delay before starting the scroll
        }

        // Method to update the text dynamically
        function updateText(newText) {
          isAnimating = false; // Stop current animation
          clearAnimations(); // Clear any ongoing animations
          text.textContent = newText; // Update the text content

          // Restart the animation after a short delay
          setTimeout(() => {
            isAnimating = true; // Resume animation
            scrollText(); // Restart the scroll with new text
          }, 500); // Short delay to allow for text to update and apply new dimensions
        }

        // Start scrolling animation
        function start() {
          isAnimating = true;
          scrollText();
        }

        // Stop scrolling animation
        function stop() {
          isAnimating = false;
          clearAnimations(); // Stop any current animations
        }

        // Immediately start the animation when this function is called
        start();

        // Return control methods for external use
        return {
          updateText,
          start,
          stop,
        };
      },
      applyScrollFadeAnimation(
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
      },
    },
  };
  </script>
  
  <style scoped>
  .scroll-container {
  }
  </style>
  