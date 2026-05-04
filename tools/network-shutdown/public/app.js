// API base URL - adjust based on deployment
const API_BASE = window.location.origin;

// Shutdown function
async function shutdown(device) {
    const button = document.getElementById(`btn-${device}`);
    const statusDiv = document.getElementById(`status-${device}`);

    // Disable button and show loading state
    button.disabled = true;
    statusDiv.className = 'status loading';
    statusDiv.innerHTML = '<span class="spinner"></span> Envoi de la commande...';

    try {
        const response = await fetch(`${API_BASE}/api/shutdown/${device}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        const data = await response.json();

        if (response.ok) {
            statusDiv.className = 'status success';
            statusDiv.innerHTML = `✓ ${data.message}`;
            
            // Re-enable button after 5 seconds
            setTimeout(() => {
                button.disabled = false;
                statusDiv.className = 'status';
                statusDiv.innerHTML = '';
            }, 5000);
        } else {
            throw new Error(data.error || 'Erreur inconnue');
        }
    } catch (error) {
        statusDiv.className = 'status error';
        statusDiv.innerHTML = `✗ Erreur: ${error.message}`;
        
        // Re-enable button after 3 seconds
        setTimeout(() => {
            button.disabled = false;
            statusDiv.className = 'status';
            statusDiv.innerHTML = '';
        }, 3000);
    }
}

// Wake on LAN function
async function wakeUp(device) {
    const button = document.getElementById(`wol-${device}`);
    const statusDiv = document.getElementById(`status-${device}`);

    button.disabled = true;
    statusDiv.className = 'status loading';
    statusDiv.innerHTML = '<span class="spinner"></span> Envoi du paquet de réveil...';

    try {
        const response = await fetch(`${API_BASE}/api/wol/${device}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        const data = await response.json();

        if (response.ok) {
            statusDiv.className = 'status success';
            statusDiv.innerHTML = `⚡ ${data.message}`;
        } else {
            throw new Error(data.error || 'Erreur inconnue');
        }
    } catch (error) {
        statusDiv.className = 'status error';
        statusDiv.innerHTML = `✗ Erreur: ${error.message}`;
    } finally {
        setTimeout(() => {
            button.disabled = false;
            statusDiv.className = 'status';
            statusDiv.innerHTML = '';
        }, 4000);
    }
}

// Refresh device status badges
async function refreshStatus() {
    const devices = ['nipogi', 'ds916', 'ds925'];
    devices.forEach(id => {
        const badge = document.getElementById(`online-${id}`);
        if (badge) { badge.className = 'online-badge checking'; badge.textContent = '…'; }
    });

    try {
        const response = await fetch(`${API_BASE}/api/status`);
        const data = await response.json();
        Object.entries(data).forEach(([id, info]) => {
            const badge = document.getElementById(`online-${id}`);
            if (badge) {
                badge.className = `online-badge ${info.online ? 'online' : 'offline'}`;
                badge.textContent = info.online ? 'En ligne' : 'Hors ligne';
            }
        });
    } catch (error) {
        devices.forEach(id => {
            const badge = document.getElementById(`online-${id}`);
            if (badge) { badge.className = 'online-badge offline'; badge.textContent = 'Erreur'; }
        });
    }
}

document.addEventListener('DOMContentLoaded', () => {
    refreshStatus();
    setInterval(refreshStatus, 30000);
});
