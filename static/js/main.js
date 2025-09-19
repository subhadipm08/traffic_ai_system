async function refreshStatus() {
  try {
    const res = await fetch("/status");
    const data = await res.json();

    // Update signals + vehicle counts
    ["NS", "SN", "EW", "WE"].forEach(lane => {
      const signal = document.getElementById(lane);
      const countEl = document.getElementById("count-" + lane);

      // Green / Red logic
      if (lane === data.green_lane) {
        signal.style.backgroundColor = "green";
      } else {
        signal.style.backgroundColor = "red";
      }

      // Vehicle count update
      if (data.vehicle_counts && data.vehicle_counts[lane] !== undefined) {
        countEl.innerText = `(${data.vehicle_counts[lane]} vehicles)`;
      }
    });

    // Status summary
    document.getElementById("status").innerText =
      `Current green lane: ${data.green_lane} | Vehicle counts: ${JSON.stringify(data.vehicle_counts)}`;
  } catch (err) {
    console.error("Error fetching status:", err);
  }
}

// Refresh every 2s
setInterval(refreshStatus, 2000);
refreshStatus(); // run immediately on load

