// Keep track of the last known counts to detect changes
let lastCounts = {};

async function refreshStatus() {
  try {
    const res = await fetch("/status");
    if (!res.ok) return;
    const data = await res.json();
    const lanes = ["NS", "SN", "EW", "WE"];

    lanes.forEach(lane => {
      const signal = document.getElementById(lane);
      const countEl = document.getElementById("count-" + lane);
      const timerEl = document.getElementById("timer-" + lane); // NEW: Get timer element

      // Update signal color and timer display
      if (lane === data.green_lane) {
          signal.style.backgroundColor = "limegreen";
          // NEW: Update timer with remaining seconds
          timerEl.innerText = `${data.time_remaining}s`;
      } else {
          signal.style.backgroundColor = "red";
          timerEl.innerText = ""; // NEW: Clear timer for red lights
      }
      
      const currentCount = data.vehicle_counts ? data.vehicle_counts[lane] : 0;
      countEl.innerText = `(${currentCount} vehicles)`;

      // If the count for a lane has changed, refresh its image
      if (lastCounts[lane] !== currentCount) {
        const img = document.getElementById("img-" + lane);
        img.src = `/processed_image/${lane}?t=${new Date().getTime()}`;
      }
    });

    // Store the new counts for the next comparison
    lastCounts = data.vehicle_counts;

  } catch (err) {
    console.error("Error fetching status:", err);
  }
}

// Refresh status every second for a smoother timer
setInterval(refreshStatus, 1000);
window.onload = refreshStatus;