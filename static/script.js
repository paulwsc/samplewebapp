// =============================================
//  main.js  —  Handsontable + explicit SAVE (commit on blur) + Authentication
// =============================================

let hot;
let originalData = [];   // immutable snapshot used for diff
let sessionToken = localStorage.getItem('sessionToken') || null;

// DOM Elements
const loginFormContainer = document.getElementById('login-form-container');
const registerFormContainer = document.getElementById('register-form-container');
const mainContent = document.getElementById('main-content');
const loginForm = document.getElementById('login-form');
const registerForm = document.getElementById('register-form');
const showRegisterLink = document.getElementById('show-register');
const showLoginLink = document.getElementById('show-login');
const logoutBtn = document.getElementById('logout-btn');
const currentUserSpan = document.getElementById('current-user');

// Check if user is already logged in on page load
window.addEventListener('load', () => {
    if (sessionToken) {
        // User has a session token, verify it
        verifySession();
    } else {
        // Show login form by default
        showLoginForm();
    }
});

// Verify session on page load
async function verifySession() {
    try {
        const response = await fetch('/user/me', {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${sessionToken}`,
                'Content-Type': 'application/json'
            }
        });

        if (response.ok) {
            const userData = await response.json();
            showMainContent(userData);
        } else {
            // Token is invalid or expired, clear it and show login
            localStorage.removeItem('sessionToken');
            sessionToken = null;
            showLoginForm();
        }
    } catch (error) {
        console.error('Error verifying session:', error);
        localStorage.removeItem('sessionToken');
        sessionToken = null;
        showLoginForm();
    }
}

// Show login form
function showLoginForm() {
    loginFormContainer.style.display = 'block';
    registerFormContainer.style.display = 'none';
    mainContent.style.display = 'none';
}

// Show registration form
function showRegisterForm() {
    loginFormContainer.style.display = 'none';
    registerFormContainer.style.display = 'block';
    mainContent.style.display = 'none';
}

// Show main content after successful login
function showMainContent(userData) {
    loginFormContainer.style.display = 'none';
    registerFormContainer.style.display = 'none';
    mainContent.style.display = 'block';

    // Update user info in header
    currentUserSpan.textContent = userData.username;

    // Load the data table
    loadData();
}

// Handle login form submission
loginForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    const formData = new FormData(loginForm);
    const username = formData.get('username');
    const password = formData.get('password');

    try {
        const response = await fetch('/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                username: username,
                password: password
            })
        });

        const data = await response.json();

        if (response.ok) {
            // Save session token
            sessionToken = data.session_token;
            localStorage.setItem('sessionToken', sessionToken);

            // Show main content
            showMainContent(data.user);

            log('Login successful');
        } else {
            log('Login failed', data.detail || data.message);
        }
    } catch (error) {
        log('Login error', error.message);
    }
});

// Handle registration form submission
registerForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    const formData = new FormData(registerForm);
    const username = formData.get('username');
    const email = formData.get('email');
    const password = formData.get('password');

    try {
        const response = await fetch('/register', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                username: username,
                email: email,
                password: password
            })
        });

        const data = await response.json();

        if (response.ok) {
            log('Registration successful. Please login.');
            showLoginForm();
        } else {
            log('Registration failed', data.detail || data.message);
        }
    } catch (error) {
        log('Registration error', error.message);
    }
});

// Toggle between login and registration forms
showRegisterLink.addEventListener('click', (e) => {
    e.preventDefault();
    showRegisterForm();
});

showLoginLink.addEventListener('click', (e) => {
    e.preventDefault();
    showLoginForm();
});

// Handle logout
logoutBtn.addEventListener('click', async () => {
    try {
        const response = await fetch('/logout', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                session_token: sessionToken
            })
        });

        if (response.ok) {
            // Clear session token
            localStorage.removeItem('sessionToken');
            sessionToken = null;

            // Show login form
            showLoginForm();

            log('Logged out successfully');
        } else {
            const data = await response.json();
            log('Logout failed', data.detail || data.message);
        }
    } catch (error) {
        log('Logout error', error.message);
    }
});

// Logging function
function log(msg, data = null) {
    const el = document.getElementById('debug');
    const ts = new Date().toISOString().slice(11,23);
    let line = `[${ts}] ${msg}`;
    if (data) line += '\n    ' + JSON.stringify(data, null, 2);
    el.textContent += line + '\n';
    el.scrollTop = el.scrollHeight;
    console.log(line, data || '');
}

// Load data function (only accessible when logged in)
async function loadData() {
    if (!sessionToken) {
        log('Not authenticated. Redirecting to login.');
        showLoginForm();
        return;
    }

    log('Fetching data...');
    try {
        const res = await fetch('/data', {
            headers: {
                'Authorization': `Bearer ${sessionToken}`
            }
        });
        if (!res.ok) throw new Error(res.statusText);
        const data = await res.json();
        originalData = structuredClone(data);  // deep copy (modern browsers)
        // or: JSON.parse(JSON.stringify(data))

        if (hot) {
            hot.loadData(data);
        } else {
            hot = new Handsontable(document.getElementById('hot'), {
                data,
                rowHeaders: true,
                colHeaders: ['ID', 'Name', 'Age', 'Email', 'Department'],
                columns: [
                    { data: 'id',   type: 'numeric', readOnly: true },
                    { data: 'name', type: 'text'     },
                    { data: 'age',  type: 'numeric'  },
                    { data: 'email', type: 'text'    },
                    { data: 'department', type: 'text' }
                ],
                stretchH: 'all',
                height: 500,
                contextMenu: true,
                manualRowMove: true,
                outsideClickDeselects: false,
                licenseKey: 'non-commercial-and-evaluation',

                afterChange(changes, source) {
                    if (source === 'loadData') return;
                    if (changes && changes.length > 0) {
                        document.getElementById('save').disabled = false;
                        log('Change detected — SAVE enabled');
                    }
                }
            });
        }
        log(`Loaded ${data.length} rows`);
    } catch (err) {
        log('Load failed', err.message);
    }
}

function computeDiff(oldData, newData) {
    const updates = [];
    const inserts = [];
    const deletes = [];

    const oldMap = new Map(oldData.map(r => [r.id, r]));
    const newMap = new Map();

    newData.forEach(row => {
        if (row.id != null) {
            newMap.set(row.id, row);
        }
    });

    // deletes
    oldData.forEach(oldRow => {
        if (oldRow.id != null && !newMap.has(oldRow.id)) {
            deletes.push(oldRow.id);
        }
    });

    // updates + inserts
    newData.forEach(row => {
        const id = row.id;
        if (id == null) {
            // new row (no id yet)
            inserts.push({ ...row }); // or clean it
            return;
        }

        const oldRow = oldMap.get(id);
        if (!oldRow) {
            inserts.push({ ...row });
            return;
        }

        const changed =
            (oldRow.name ?? '') !== (row.name ?? '') ||
            Number(oldRow.age ?? NaN) !== Number(row.age ?? NaN) ||
            (oldRow.email ?? '') !== (row.email ?? '') ||
            (oldRow.department ?? '') !== (row.department ?? '');

        if (changed) {
            updates.push({
                id,
                data: {
                    name: row.name ?? null,
                    age: row.age != null ? Number(row.age) : null,
                    email: row.email ?? null,
                    department: row.department ?? null
                }
            });
        }
    });

    return { updates, inserts, deletes };
}

async function saveChanges() {
    if (!sessionToken) {
        log('Not authenticated. Redirecting to login.');
        showLoginForm();
        return;
    }

    log('Saving...');
    document.getElementById('save').disabled = true;

    const current = hot.getSourceData();
    const diff = computeDiff(originalData, current);

    log('Diff', diff);

    try {
        // updates
        for (const { id, data } of diff.updates) {
            log(`PUT /data/${id}`);
            const res = await fetch(`/data/${id}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${sessionToken}`
                },
                body: JSON.stringify(data)
            });
            if (!res.ok) throw new Error(await res.text());
        }

        // inserts
        for (const row of diff.inserts) {
            log('POST /data');
            const res = await fetch('/data', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${sessionToken}`
                },
                body: JSON.stringify(row)
            });
            if (!res.ok) throw new Error(await res.text());
        }

        // deletes
        for (const id of diff.deletes) {
            log(`DELETE /data/${id}`);
            const res = await fetch(`/data/${id}`, {
                method: 'DELETE',
                headers: {
                    'Authorization': `Bearer ${sessionToken}`
                }
            });
            if (!res.ok) throw new Error(await res.text());
        }

        log('Save successful → reloading');
        await loadData();
    } catch (err) {
        log('Save failed', err.message);
        document.getElementById('save').disabled = false;
    }
}

// ─── button handlers ─────────────────────────────────────

document.getElementById('save').onclick = saveChanges;

document.getElementById('add').onclick = () => {
    if (!sessionToken) {
        log('Not authenticated. Redirecting to login.');
        showLoginForm();
        return;
    }

    hot.alter('insert_row_below', hot.countRows());
    document.getElementById('save').disabled = false;
    log('Row added');
};

document.getElementById('delete').onclick = () => {
    if (!sessionToken) {
        log('Not authenticated. Redirecting to login.');
        showLoginForm();
        return;
    }

    const selection = hot.getSelected() || [];
    if (!selection.length) {
        log('No rows selected');
        return;
    }

    const rows = new Set();
    selection.forEach(([r1, , r2]) => {
        for (let r = Math.min(r1, r2); r <= Math.max(r1, r2); r++) {
            rows.add(r);
        }
    });

    [...rows].sort((a,b)=>b-a).forEach(r => hot.alter('remove_row', r));
    document.getElementById('save').disabled = false;
    log(`Marked ${rows.size} rows for deletion`);
};

document.getElementById('clear').onclick = () => {
    document.getElementById('debug').textContent = '';
};