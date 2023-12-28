function setupScrollingText(containerId, textId) {
    const textContainer = document.getElementById(containerId);
    const text = document.getElementById(textId);

    function scrollText() {
        const textWidth = text.offsetWidth;
        const containerWidth = textContainer.offsetWidth;
        const scrollingDuration = (textWidth / containerWidth) * 5; // Adjust this for speed

        // Apply the scrolling
        text.style.transition = `left ${scrollingDuration}s linear`;
        text.style.left = `-${textWidth - containerWidth}px`;

        // Wait for the text to finish scrolling
        setTimeout(() => {
            // Fade out text
            text.style.opacity = '0';

            // Reset position and opacity, then restart animation
            setTimeout(() => {
                text.style.transition = 'none'; // Disable transition for instant reset
                text.style.left = '0';
                text.style.opacity = '1';

                // Add a slight delay before restarting the animation
                setTimeout(() => {
                    text.style.transition = `left ${scrollingDuration}s linear`; // Re-enable transition
                    scrollText(); // Restart the animation
                }, 100); // Short delay before restarting
            }, 2000); // Time before restarting the animation
        }, scrollingDuration * 1000); // Convert seconds to milliseconds
    }

    scrollText();
}