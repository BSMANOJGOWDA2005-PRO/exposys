// State Management
let currentCandidates = [];
let activeCandidate = null;

// DOM Elements
const senderNameInput = document.getElementById('senderName');
const senderRollInput = document.getElementById('senderRoll');
const updateBtn = document.getElementById('updateSenderBtn');
const totalCandidatesEl = document.getElementById('totalCandidates');
const selectedCandidatesEl = document.getElementById('selectedCandidates');
const highestScoreEl = document.getElementById('highestScore');
const averageScoreEl = document.getElementById('averageScore');
const tableBodyEl = document.getElementById('candidatesTableBody');
const alertContainerEl = document.getElementById('alertContainer');

// Modal Elements
const messageModal = document.getElementById('messageModal');
const modalCandidateName = document.getElementById('modalCandidateName');
const modalCandidatePhone = document.getElementById('modalCandidatePhone');
const modalMessageText = document.getElementById('modalMessageText');
const modalCopyBtn = document.getElementById('modalCopyBtn');
const modalWhatsAppBtn = document.getElementById('modalWhatsAppBtn');
const modalWhatsAppWebBtn = document.getElementById('modalWhatsAppWebBtn');
const modalAutoSendBtn = document.getElementById('modalAutoSendBtn');
const modalCloseBtn = document.getElementById('modalCloseBtn');
const toastContainer = document.getElementById('toastContainer');

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    // Load persisted sender data from localStorage if available
    const savedName = localStorage.getItem('exposys_sender_name');
    const savedRoll = localStorage.getItem('exposys_sender_roll');
    if (savedName) senderNameInput.value = savedName;
    if (savedRoll) senderRollInput.value = savedRoll;

    // Fetch initial candidate list
    fetchCandidates();

    // Event Listeners
    updateBtn.addEventListener('click', handleSenderUpdate);
    senderNameInput.addEventListener('keypress', (e) => { if (e.key === 'Enter') handleSenderUpdate(); });
    senderRollInput.addEventListener('keypress', (e) => { if (e.key === 'Enter') handleSenderUpdate(); });

    modalCloseBtn.addEventListener('click', closeModal);
    messageModal.addEventListener('click', (e) => {
        if (e.target === messageModal) closeModal();
    });

    modalCopyBtn.addEventListener('click', () => {
        if (modalMessageText.textContent) {
            copyToClipboard(modalMessageText.textContent);
        }
    });

    if (modalAutoSendBtn) {
        modalAutoSendBtn.addEventListener('click', triggerAutoSend);
    }

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && messageModal.classList.contains('active')) {
            closeModal();
        }
    });
});

// Update sender details and re-fetch / update messages
function handleSenderUpdate() {
    const name = senderNameInput.value.trim();
    const roll = senderRollInput.value.trim();
    
    localStorage.setItem('exposys_sender_name', name);
    localStorage.setItem('exposys_sender_roll', roll);

    showToast('Sender info updated. Messages regenerated.', 'success');
    fetchCandidates();
}

// Fetch candidates from Flask REST API
async function fetchCandidates() {
    try {
        const yourName = encodeURIComponent(senderNameInput.value.trim());
        const rollNumber = encodeURIComponent(senderRollInput.value.trim());
        
        const response = await fetch(`/api/top6?your_name=${yourName}&roll_number=${rollNumber}`);
        const data = await response.json();

        if (!data.success) {
            showToast(data.error || 'Failed to load candidates', 'error');
            return;
        }

        currentCandidates = data.top6 || [];
        updateSummaryCards(data);
        renderTable(currentCandidates);

        // Warning banner if fewer than 6 candidates
        if (data.has_less_than_6) {
            alertContainerEl.innerHTML = `
                <div class="alert-box alert-warning">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <circle cx="12" cy="12" r="10"></circle>
                        <line x1="12" y1="8" x2="12" y2="12"></line>
                        <line x1="12" y1="16" x2="12.01" y2="16"></line>
                    </svg>
                    <span>Note: Dataset contains ${data.total_candidates} candidate(s). All available candidates have been displayed.</span>
                </div>
            `;
        } else {
            alertContainerEl.innerHTML = '';
        }

    } catch (err) {
        console.error('Error fetching candidates:', err);
        showToast('Error communicating with backend server', 'error');
    }
}

// Update summary stats
function updateSummaryCards(data) {
    totalCandidatesEl.textContent = data.total_candidates;
    selectedCandidatesEl.textContent = data.selected_candidates_count;
    highestScoreEl.textContent = data.highest_score;
    averageScoreEl.textContent = data.average_score;
}

// Render candidates in Table
function renderTable(candidates) {
    tableBodyEl.innerHTML = '';

    if (candidates.length === 0) {
        tableBodyEl.innerHTML = `
            <tr>
                <td colspan="6" style="text-align: center; padding: 2rem; color: var(--text-muted);">
                    No candidates found. Please ensure dataset/dataset.csv exists with valid entries.
                </td>
            </tr>
        `;
        return;
    }

    candidates.forEach((c) => {
        const tr = document.createElement('tr');

        // Rank badge style class
        let rankClass = 'rank-other';
        if (c.rank === 1) rankClass = 'rank-1';
        else if (c.rank === 2) rankClass = 'rank-2';
        else if (c.rank === 3) rankClass = 'rank-3';

        tr.innerHTML = `
            <td>
                <span class="rank-badge ${rankClass}">
                    ★ Rank ${c.rank}
                </span>
            </td>
            <td>
                <span class="candidate-name">${escapeHtml(c.name)}</span>
            </td>
            <td>
                <span class="candidate-phone">+${escapeHtml(c.phone)}</span>
            </td>
            <td>
                <span class="score-badge">${c.score}</span>
            </td>
            <td>
                <span class="status-badge">
                    <span class="status-dot"></span>
                    ${c.status}
                </span>
            </td>
            <td>
                <div class="table-actions">
                    <button class="btn btn-outline btn-sm view-btn" data-id="${c.id}">
                        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
                            <circle cx="12" cy="12" r="3"></circle>
                        </svg>
                        View Message
                    </button>
                    <a href="${c.whatsapp_url}" target="_blank" rel="noopener noreferrer" class="btn btn-whatsapp btn-sm">
                        <svg width="15" height="15" viewBox="0 0 24 24" fill="currentColor">
                            <path d="M.057 24l1.687-6.163c-1.041-1.804-1.588-3.849-1.587-5.946.003-6.556 5.338-11.891 11.893-11.891 3.181.001 6.167 1.24 8.413 3.488 2.245 2.248 3.481 5.236 3.48 8.414-.003 6.557-5.338 11.892-11.893 11.892-1.99-.001-3.951-.5-5.688-1.448l-6.305 1.654zm6.597-3.807c1.676.995 3.276 1.591 5.392 1.592 5.448 0 9.886-4.434 9.889-9.885.002-5.462-4.415-9.89-9.881-9.892-5.452 0-9.887 4.434-9.889 9.884-.001 2.225.651 3.891 1.746 5.634l-.999 3.648 3.742-.981zm11.387-5.464c-.074-.124-.272-.198-.57-.347-.297-.149-1.758-.868-2.031-.967-.272-.099-.47-.149-.669.149-.198.297-.768.967-.941 1.165-.173.198-.347.223-.644.074-.297-.149-1.255-.462-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.297-.347.446-.521.151-.172.2-.296.3-.495.099-.198.05-.372-.025-.521-.075-.148-.669-1.611-.916-2.206-.242-.579-.487-.501-.669-.51l-.57-.01c-.198 0-.52.074-.792.372s-1.04 1.016-1.04 2.479 1.065 2.876 1.213 3.074c.149.198 2.095 3.2 5.076 4.487.709.306 1.263.489 1.694.626.712.226 1.36.194 1.872.118.571-.085 1.758-.719 2.006-1.413.248-.695.248-1.29.173-1.414z"/>
                        </svg>
                        Send WhatsApp
                    </a>
                </div>
            </td>
        `;

        tableBodyEl.appendChild(tr);
    });

    // Attach click events for View Message buttons
    document.querySelectorAll('.view-btn').forEach((btn) => {
        btn.addEventListener('click', (e) => {
            const candId = parseInt(btn.getAttribute('data-id'), 10);
            const candidate = currentCandidates.find(c => c.id === candId);
            if (candidate) {
                openModal(candidate);
            }
        });
    });
}

// WhatsApp Dispatcher (Universal wa.me + WhatsApp Web fallback)
function openWhatsApp(candidate) {
    if (!candidate || !candidate.phone) {
        showToast('Invalid candidate phone number', 'error');
        return;
    }

    // Standard universal URL for mobile app & desktop WhatsApp
    const universalUrl = candidate.whatsapp_url;
    // Direct WhatsApp Web browser URL
    const webUrl = candidate.whatsapp_web_url || `https://web.whatsapp.com/send?phone=${candidate.phone}&text=${encodeURIComponent(candidate.personalized_message)}`;

    // Open universal link
    const win = window.open(universalUrl, '_blank');
    if (!win || win.closed || typeof win.closed === 'undefined') {
        // Pop-up blocker triggered: fallback to direct location
        window.location.href = universalUrl;
    }
}

// Open Message Modal
function openModal(candidate) {
    activeCandidate = candidate;
    modalCandidateName.textContent = candidate.name;
    modalCandidatePhone.textContent = `+${candidate.phone}`;
    modalMessageText.textContent = candidate.personalized_message;
    modalWhatsAppBtn.href = candidate.whatsapp_url;
    
    const webBtn = document.getElementById('modalWhatsAppWebBtn');
    if (webBtn) {
        webBtn.href = candidate.whatsapp_web_url || `https://web.whatsapp.com/send?phone=${candidate.phone}&text=${encodeURIComponent(candidate.personalized_message)}`;
    }

    modalWhatsAppBtn.onclick = (e) => {
        // Also copy text to clipboard as convenient backup before WhatsApp opens
        copyToClipboardSilently(candidate.personalized_message);
    };
    messageModal.classList.add('active');
}

// Automated WhatsApp Sender (Opens & Automatically Presses Send)
async function triggerAutoSend() {
    if (!activeCandidate) {
        showToast('No candidate selected', 'error');
        return;
    }

    try {
        const yourName = senderNameInput.value.trim();
        const rollNumber = senderRollInput.value.trim();

        // Also copy text to clipboard as safety backup
        copyToClipboardSilently(activeCandidate.personalized_message);

        showToast(`Opening WhatsApp for ${activeCandidate.name}... Sending automatically in 12s.`, 'success');

        const response = await fetch('/api/send_whatsapp_auto', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                id: activeCandidate.id,
                your_name: yourName,
                roll_number: rollNumber,
                wait_seconds: 12
            })
        });

        const data = await response.json();
        if (data.success) {
            showToast('Automation dispatched! Keep browser focused on WhatsApp Web.', 'success');
        } else {
            showToast(data.error || 'Failed to trigger automated send', 'error');
        }
    } catch (err) {
        console.error('Auto send error:', err);
        showToast('Error communicating with automation server', 'error');
    }
}

// Close Message Modal
function closeModal() {
    messageModal.classList.remove('active');
    activeCandidate = null;
}

// Silent clipboard copy for convenient backup
function copyToClipboardSilently(text) {
    if (navigator.clipboard) {
        navigator.clipboard.writeText(text).catch(() => {});
    }
}

// Copy to Clipboard
async function copyToClipboard(text) {
    try {
        await navigator.clipboard.writeText(text);
        showToast('Message copied to clipboard!', 'success');
    } catch (err) {
        // Fallback for older browsers or permission limitations
        const textArea = document.createElement('textarea');
        textArea.value = text;
        textArea.style.position = 'fixed';
        textArea.style.opacity = '0';
        document.body.appendChild(textArea);
        textArea.select();
        try {
            document.execCommand('copy');
            showToast('Message copied to clipboard!', 'success');
        } catch (copyErr) {
            showToast('Failed to copy message', 'error');
        }
        document.body.removeChild(textArea);
    }
}

// Toast Notification
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    
    let iconSvg = '';
    if (type === 'success') {
        iconSvg = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#25d366" stroke-width="2.5"><polyline points="20 6 9 17 4 12"></polyline></svg>`;
    } else if (type === 'error') {
        iconSvg = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#ef4444" stroke-width="2.5"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>`;
    }

    toast.innerHTML = `${iconSvg} <span>${escapeHtml(message)}</span>`;
    toastContainer.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(10px)';
        toast.style.transition = 'all 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 3500);
}

// Basic HTML escaping
function escapeHtml(str) {
    if (!str) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}
