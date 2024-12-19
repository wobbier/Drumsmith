<template>
    <div id="game">
        <div class="line target-line"></div>
        <div class="line moving-line"></div>
    </div>
    <p id="message">Press any key when the moving line aligns with the target line.</p>
    <p id="average">Average Accuracy: N/A</p>
</template>

<script>
export default {
    data() {
        return {
            ringBufferSize: 10,
            accuracies: [],
            currentIndex: 0,
        };
    },
    mounted() {
        this.accuracies = Array(this.ringBufferSize).fill(null); // Initialize with null values
        document.addEventListener("keydown", () => {
            const movingLine = document.querySelector(".moving-line");
            const targetLine = document.querySelector(".target-line");

            // Get the positions of the moving and target lines
            const movingRect = movingLine.getBoundingClientRect();
            const targetRect = targetLine.getBoundingClientRect();

            const movingCenter = movingRect.left + movingRect.width / 2;
            const targetCenter = targetRect.left + targetRect.width / 2;

            // Calculate accuracy (distance between centers)
            const accuracy = Math.abs(movingCenter - targetCenter);

            // Add the current accuracy to the ring buffer
            this.accuracies[this.currentIndex] = accuracy;
            this.currentIndex = (this.currentIndex + 1) % this.ringBufferSize; // Wrap around to the start

            // Calculate the average excluding null values
            const validAccuracies = this.accuracies.filter(value => value !== null);
            const averageAccuracy =
                validAccuracies.reduce((sum, value) => sum + value, 0) / validAccuracies.length;

            const message = document.getElementById("message");
            if (accuracy < 10) {
                message.textContent = "Great timing! Accuracy: " + accuracy.toFixed(2) + "px";
            } else {
                message.textContent = "Missed! Accuracy: " + accuracy.toFixed(2) + "px";
            }

            document.getElementById("average").textContent =
                `Average Accuracy (last ${validAccuracies.length} attempts): ${averageAccuracy.toFixed(2)}px`;
        });
    }
}

</script>

<style>
#game {
    position: relative;
    width: 500px;
    height: 200px;
    background-color: #333;
    margin-bottom: 20px;
    border: 2px solid #555;
}

.line {
    position: absolute;
    width: 2px;
    height: 100%;
    background-color: white;
}

.target-line {
    left: 50%;
    /* Target is in the center */
}

.moving-line {
    animation: move-back-and-forth 2s linear infinite;
    color: #fefefe;
}

@keyframes move-back-and-forth {
    0% {
        left: 0%;
    }

    50% {
        left: 100%;
    }

    100% {
        left: 0%;
    }
}

#message {
    font-size: 16px;
    text-align: center;
}
</style>