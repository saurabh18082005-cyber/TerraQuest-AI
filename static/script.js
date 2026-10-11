
const form = document.getElementById("mission-form");
const generateButton = document.getElementById("generate-button");
const result = document.getElementById("mission-result");
const completeButton = document.getElementById("complete-button");

form.addEventListener("submit", async (event) => {
    event.preventDefault();

    generateButton.disabled = true;
    generateButton.textContent = "Creating your mission...";
    result.hidden = true;

    const payload = {
        activity: document.getElementById("activity").value,
        duration: document.getElementById("duration").value,
        difficulty: document.getElementById("difficulty").value,
        interests: document.getElementById("interests").value.trim()
    };

    try {
        const response = await fetch("/api/mission", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        const mission = await response.json();

        if (!response.ok) {
            throw new Error(mission.error || "Could not create your mission.");
        }

        document.getElementById("mission-title").textContent = mission.title;
        document.getElementById("mission-description").textContent =
            mission.description;
        document.getElementById("mission-meta").textContent =
            `${mission.duration} minutes · ${mission.difficulty}`;

        const steps = document.getElementById("mission-steps");
        steps.replaceChildren();

        mission.steps.forEach((step) => {
            const item = document.createElement("li");
            item.textContent = step;
            steps.appendChild(item);
        });

        document.getElementById("reflection").value = "";
        document.getElementById("completion-message").textContent = "";
        result.hidden = false;
        result.scrollIntoView({ behavior: "smooth", block: "start" });
    } catch (error) {
        alert(error.message || "Something went wrong. Please try again.");
    } finally {
        generateButton.disabled = false;
        generateButton.innerHTML = 'Create my mission <span>→</span>';
    }
});

completeButton.addEventListener("click", () => {
    const reflection = document.getElementById("reflection").value.trim();
    const message = document.getElementById("completion-message");

    message.textContent = reflection
        ? "Mission marked complete! Your discovery has been recorded for this session. 🌱"
        : "Mission marked complete! Add a reflection whenever you're ready. 🌱";
});

document.querySelectorAll(".activity-card").forEach((card) => {
    card.addEventListener("click", () => {
        const activity = card.dataset.activity;

        document.getElementById("activity").value = activity;

        document.querySelectorAll(".activity-card").forEach((item) => {
            item.classList.toggle("selected", item === card);
        });
    });
});
// TerraQuest AI — responsive camera, image upload, and nearby leaderboard
(() => {
    const $ = (id) => document.getElementById(id);
    const imageInput = $("discovery-image");
    const chooseButton = $("choose-image");
    const changeButton = $("change-image");
    const uploadArea = $("scan-upload-area");
    const previewSection = $("scan-preview");
    const previewImage = $("discovery-preview-image");
    const identifyButton = $("identify-discovery");
    const status = $("scan-status");
    const openCameraButton = $("open-camera");
    const cameraPanel = $("camera-panel");
    const video = $("camera-video");
    const canvas = $("camera-canvas");
    const takePhotoButton = $("take-photo");
    const closeCameraButton = $("close-camera");

    let selectedFile = null;
    let previewUrl = null;
    let cameraStream = null;
    let nearbyCoords = null;

    const setStatus = (message) => { if (status) status.textContent = message; };

    function stopCamera() {
        if (cameraStream) cameraStream.getTracks().forEach((track) => track.stop());
        cameraStream = null;
        if (video) video.srcObject = null;
        if (cameraPanel) cameraPanel.hidden = true;
    }

    function selectPhoto(file) {
        if (!file || !file.type.startsWith("image/")) {
            setStatus("Please select a valid image file.");
            return;
        }
        if (file.size > 10 * 1024 * 1024) {
            setStatus("Please choose an image smaller than 10 MB.");
            return;
        }
        if (previewUrl) URL.revokeObjectURL(previewUrl);
        selectedFile = file;
        previewUrl = URL.createObjectURL(file);
        previewImage.src = previewUrl;
        previewSection.hidden = false;
        uploadArea.hidden = true;
        if ($("discovery-result")) $("discovery-result").hidden = true;
        setStatus("Photo ready. Choose Identify discovery when you're ready.");
    }

    if (chooseButton && imageInput) chooseButton.addEventListener("click", () => imageInput.click());
    if (changeButton && imageInput) changeButton.addEventListener("click", () => imageInput.click());
    if (imageInput) imageInput.addEventListener("change", () => {
        const file = imageInput.files && imageInput.files[0];
        if (file) selectPhoto(file);
        imageInput.value = "";
    });

    // Mobile browsers require a secure context (HTTPS or localhost) and permission.
    if (openCameraButton) openCameraButton.addEventListener("click", async () => {
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            setStatus("Camera access needs HTTPS or localhost on this browser. You can still upload a photo.");
            return;
        }
        try {
            stopCamera();
            cameraStream = await navigator.mediaDevices.getUserMedia({
                audio: false,
                video: { facingMode: { ideal: "environment" }, width: { ideal: 1280 }, height: { ideal: 720 } }
            });
            video.srcObject = cameraStream;
            cameraPanel.hidden = false;
            await video.play();
            setStatus("Camera is ready. Frame your discovery and take a photo.");
        } catch (error) {
            setStatus(error.name === "NotAllowedError"
                ? "Camera permission was denied. Allow camera access in browser settings or upload a photo."
                : "Could not open the camera. Try uploading a photo instead.");
        }
    });

    if (takePhotoButton) takePhotoButton.addEventListener("click", () => {
        if (!video.videoWidth || !video.videoHeight) {
            setStatus("Wait for the camera preview to load, then try again.");
            return;
        }
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        canvas.getContext("2d").drawImage(video, 0, 0, canvas.width, canvas.height);
        canvas.toBlob((blob) => {
            if (!blob) { setStatus("Photo capture failed. Please try again."); return; }
            selectPhoto(new File([blob], `terraquest-${Date.now()}.jpg`, { type: "image/jpeg" }));
            stopCamera();
        }, "image/jpeg", 0.9);
    });
    if (closeCameraButton) closeCameraButton.addEventListener("click", stopCamera);

    if (identifyButton) identifyButton.addEventListener("click", async () => {
        if (!selectedFile) { setStatus("Upload or take a photo first."); return; }
        identifyButton.disabled = true;
        setStatus("Submitting photo for identification...");
        try {
            const body = new FormData();
            body.append("image", selectedFile);
            const response = await fetch("/api/identify", { method: "POST", body });
            const data = await response.json();
            if (!response.ok) throw new Error(data.error || "Identification service unavailable.");
            $("result-species").textContent = data.species || "Unknown species";
            $("result-scientific-name").textContent = data.scientific_name || "Scientific name unavailable";
            $("result-rarity").textContent = data.rarity || "Unverified";
            $("result-points").textContent = String(data.points ?? 0);
            $("result-verification").textContent = data.verification || "Unverified";
            $("result-explanation").textContent = data.explanation || "More evidence is needed to verify this discovery.";
            $("discovery-result").hidden = false;
            setStatus("Discovery report received.");
        } catch (error) {
            setStatus(error.message || "Identification failed. The vision-model endpoint may not be configured yet.");
        } finally { identifyButton.disabled = false; }
    });

    // Opt-in geolocation; browser sends coordinates only after user presses the button.
    async function loadNearbyLeaderboard() {
        const statusEl = $("leaderboard-status");
        const list = $("leaderboard-list");
        if (!statusEl || !list) return;
        if (!nearbyCoords) {
            statusEl.textContent = "Choose “Use my current location” to find nearby explorers.";
            return;
        }
        statusEl.textContent = "Finding the Top 10 nearby explorers...";
        list.replaceChildren();
        try {
            const params = new URLSearchParams({ lat: nearbyCoords.latitude, lon: nearbyCoords.longitude });
            const response = await fetch(`/api/leaderboard?${params.toString()}`);
            const data = await response.json();
            if (!response.ok) throw new Error(data.error || "Leaderboard request failed.");
            const explorers = Array.isArray(data.explorers) ? data.explorers : [];
            if (!explorers.length) {
                statusEl.textContent = "No local explorers have earned points in the shared leaderboard yet. Be an early explorer!";
                return;
            }
            const fragment = document.createDocumentFragment();
            explorers.slice(0, 10).forEach((entry, index) => {
                const row = document.createElement("div"); row.className = "leaderboard-row";
                const rank = document.createElement("span"); rank.className = "leaderboard-rank"; rank.textContent = `#${entry.rank || index + 1}`;
                const player = document.createElement("div"); player.className = "leaderboard-player";
                const name = document.createElement("strong"); name.textContent = entry.name || "Nature Explorer";
                const details = document.createElement("span"); details.textContent = `${Number(entry.discoveries) || 0} verified discoveries · ${entry.area || "Nearby"}`;
                player.append(name, details);
                const score = document.createElement("span"); score.className = "leaderboard-score"; score.textContent = `${Number(entry.points) || 0} pts`;
                row.append(rank, player, score); fragment.appendChild(row);
            });
            list.appendChild(fragment);
            statusEl.textContent = `Top ${explorers.length} explorers near your approximate location.`;
        } catch (error) {
            statusEl.textContent = error.message || "Could not load nearby leaderboard.";
        }
    }

    const locationButton = $("share-location");
    if (locationButton) locationButton.addEventListener("click", () => {
        if (!navigator.geolocation) {
            $("leaderboard-status").textContent = "Location is not supported by this browser. You can still use TerraQuest.";
            return;
        }
        locationButton.disabled = true;
        $("leaderboard-status").textContent = "Requesting your permission for approximate location...";
        navigator.geolocation.getCurrentPosition((position) => {
            nearbyCoords = { latitude: position.coords.latitude, longitude: position.coords.longitude };
            const explorerName = ($("explorer-name")?.value || "Nature Explorer").trim();
            fetch("/api/profile", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ name: explorerName || "Nature Explorer", lat: nearbyCoords.latitude, lon: nearbyCoords.longitude })
            }).then(async (response) => {
                const payload = await response.json();
                if (!response.ok) throw new Error(payload.error || "Could not save explorer profile.");
            }).then(loadNearbyLeaderboard).catch((error) => {
                $("leaderboard-status").textContent = error.message || "Could not save your profile.";
            }).finally(() => { locationButton.disabled = false; });
        }, (error) => {
            locationButton.disabled = false;
            $("leaderboard-status").textContent = error.code === 1
                ? "Location permission was declined. Enable it in browser settings if you want nearby rankings."
                : "Could not determine your location. Try again or check device location settings.";
        }, { enableHighAccuracy: false, timeout: 10000, maximumAge: 300000 });
    });
    const refresh = $("refresh-leaderboard");
    if (refresh) refresh.addEventListener("click", loadNearbyLeaderboard);

    window.addEventListener("pagehide", () => {
        stopCamera();
        if (previewUrl) URL.revokeObjectURL(previewUrl);
    });
})();
