// ===== 일정 관리 (집보기 예약, 계약, 미팅) =====

function showScheduleForm(editId) {
    const schedule = editId ? DB.findById('schedules', editId) : null;
    const title = schedule ? '일정 수정' : '일정 등록';
    const customers = DB.get('customers');
    const properties = DB.get('properties');

    const html = `
        <div class="modal-title">
            ${title}
            <button class="modal-close" onclick="closeModal()">&times;</button>
        </div>
        <form onsubmit="saveSchedule(event, '${editId || ''}')">
            <div class="form-group">
                <label class="form-label">일정유형 *</label>
                <select class="form-select" id="schedType" required>
                    <option value="">선택하세요</option>
                    <option value="viewing" ${schedule?.type === 'viewing' ? 'selected' : ''}>집보기</option>
                    <option value="contract" ${schedule?.type === 'contract' ? 'selected' : ''}>계약</option>
                    <option value="meeting" ${schedule?.type === 'meeting' ? 'selected' : ''}>미팅</option>
                </select>
            </div>
            <div class="form-group">
                <label class="form-label">제목 *</label>
                <input type="text" class="form-input" id="schedTitle" required
                    value="${schedule?.title || ''}" placeholder="예: 역삼동 아파트 집보기">
            </div>
            <div class="form-row">
                <div class="form-group">
                    <label class="form-label">날짜 *</label>
                    <input type="date" class="form-input" id="schedDate" required
                        value="${schedule?.date || getTodayStr()}">
                </div>
                <div class="form-group">
                    <label class="form-label">시간 *</label>
                    <input type="time" class="form-input" id="schedTime" required
                        value="${schedule?.time || '14:00'}">
                </div>
            </div>
            <div class="form-group">
                <label class="form-label">고객 선택</label>
                <select class="form-select" id="schedCustomer">
                    <option value="">선택하세요</option>
                    ${customers.map(c =>
                        `<option value="${c.id}" ${schedule?.customerId === c.id ? 'selected' : ''}>${c.name} (${CUSTOMER_TYPES[c.type]})</option>`
                    ).join('')}
                </select>
            </div>
            <div class="form-group">
                <label class="form-label">관련 매물</label>
                <select class="form-select" id="schedProperty">
                    <option value="">선택하세요</option>
                    ${properties.map(p =>
                        `<option value="${p.id}" ${schedule?.propertyId === p.id ? 'selected' : ''}>${PROPERTY_TYPES[p.type]} - ${p.address}</option>`
                    ).join('')}
                </select>
            </div>
            <div class="form-group">
                <label class="form-label">장소</label>
                <input type="text" class="form-input" id="schedLocation"
                    value="${schedule?.location || ''}" placeholder="현장, 사무실, 카페 등">
            </div>
            <div class="form-group">
                <label class="form-label">상태</label>
                <select class="form-select" id="schedStatus">
                    <option value="confirmed" ${schedule?.status === 'confirmed' ? 'selected' : ''}>확정</option>
                    <option value="pending" ${!schedule || schedule?.status === 'pending' ? 'selected' : ''}>대기</option>
                    <option value="cancelled" ${schedule?.status === 'cancelled' ? 'selected' : ''}>취소</option>
                    <option value="completed" ${schedule?.status === 'completed' ? 'selected' : ''}>완료</option>
                </select>
            </div>
            <div class="form-group">
                <label class="form-label">메모</label>
                <textarea class="form-textarea" id="schedMemo" placeholder="참고사항">${schedule?.memo || ''}</textarea>
            </div>
            <div class="form-actions">
                <button type="button" class="btn btn-outline btn-full" onclick="closeModal()">취소</button>
                <button type="submit" class="btn btn-primary btn-full">저장</button>
            </div>
        </form>
    `;
    openModal(html);
}

function saveSchedule(e, editId) {
    e.preventDefault();
    const data = {
        type: document.getElementById('schedType').value,
        title: document.getElementById('schedTitle').value.trim(),
        date: document.getElementById('schedDate').value,
        time: document.getElementById('schedTime').value,
        customerId: document.getElementById('schedCustomer').value,
        propertyId: document.getElementById('schedProperty').value,
        location: document.getElementById('schedLocation').value.trim(),
        status: document.getElementById('schedStatus').value,
        memo: document.getElementById('schedMemo').value.trim()
    };

    if (editId) {
        DB.update('schedules', editId, data);
        showToast('일정이 수정되었습니다');
    } else {
        DB.add('schedules', data);
        showToast('일정이 등록되었습니다');
    }

    closeModal();
    renderSchedules();
    updateDashboard();
}

function renderSchedules(typeFilter) {
    let schedules = DB.get('schedules');

    if (typeFilter && typeFilter !== 'all') {
        schedules = schedules.filter(s => s.type === typeFilter);
    }

    // 날짜+시간 순 정렬
    schedules.sort((a, b) => {
        const dateA = a.date + ' ' + a.time;
        const dateB = b.date + ' ' + b.time;
        return dateA.localeCompare(dateB);
    });

    const container = document.getElementById('scheduleList');
    if (schedules.length === 0) {
        container.innerHTML = '<div class="empty-state">등록된 일정이 없습니다</div>';
        return;
    }

    container.innerHTML = schedules.map(s => {
        const customer = s.customerId ? DB.findById('customers', s.customerId) : null;
        const isTodaySchedule = isToday(s.date);

        return `
            <div class="list-item ${isTodaySchedule ? 'today-highlight' : ''}" onclick="showScheduleDetail('${s.id}')">
                <div class="list-item-header">
                    <span class="list-item-name">${formatDateTime(s.date, s.time)}</span>
                    <span class="badge badge-${s.status}">${SCHEDULE_STATUS[s.status]}</span>
                </div>
                <div style="display:flex;align-items:center;gap:6px;margin-top:4px;">
                    <span class="badge badge-${s.type}">${SCHEDULE_TYPES[s.type]}</span>
                    <span style="font-size:14px;font-weight:600;">${s.title}</span>
                </div>
                ${customer ? `<div class="list-item-sub">고객: ${customer.name}</div>` : ''}
                ${s.location ? `<div class="list-item-sub">장소: ${s.location}</div>` : ''}
            </div>
        `;
    }).join('');
}

function showScheduleDetail(id) {
    const s = DB.findById('schedules', id);
    if (!s) return;

    const customer = s.customerId ? DB.findById('customers', s.customerId) : null;
    const property = s.propertyId ? DB.findById('properties', s.propertyId) : null;

    const html = `
        <div class="modal-title">
            일정 상세
            <button class="modal-close" onclick="closeModal()">&times;</button>
        </div>
        <div class="detail-section">
            <div class="detail-row">
                <span class="detail-label">유형</span>
                <span class="detail-value"><span class="badge badge-${s.type}">${SCHEDULE_TYPES[s.type]}</span> <span class="badge badge-${s.status}">${SCHEDULE_STATUS[s.status]}</span></span>
            </div>
            <div class="detail-row">
                <span class="detail-label">제목</span>
                <span class="detail-value">${s.title}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">일시</span>
                <span class="detail-value">${formatDateTime(s.date, s.time)}</span>
            </div>
            ${customer ? `<div class="detail-row"><span class="detail-label">고객</span><span class="detail-value">${customer.name} (${formatPhone(customer.phone)})</span></div>` : ''}
            ${property ? `<div class="detail-row"><span class="detail-label">매물</span><span class="detail-value">${PROPERTY_TYPES[property.type]} - ${property.address}</span></div>` : ''}
            ${s.location ? `<div class="detail-row"><span class="detail-label">장소</span><span class="detail-value">${s.location}</span></div>` : ''}
            ${s.memo ? `<div class="detail-row"><span class="detail-label">메모</span><span class="detail-value">${s.memo}</span></div>` : ''}
        </div>

        ${s.status !== 'cancelled' && s.status !== 'completed' ? `
        <div class="form-actions">
            <button class="btn btn-success btn-full" onclick="updateScheduleStatus('${s.id}', 'completed')">완료</button>
            <button class="btn btn-danger btn-full" onclick="updateScheduleStatus('${s.id}', 'cancelled')">취소</button>
        </div>
        ` : ''}
        <div class="form-actions">
            <button class="btn btn-outline btn-full" onclick="showScheduleForm('${s.id}')">수정</button>
            <button class="btn btn-danger btn-full" onclick="deleteSchedule('${s.id}')">삭제</button>
        </div>
    `;
    openModal(html);
}

function updateScheduleStatus(id, status) {
    const statusText = SCHEDULE_STATUS[status];
    DB.update('schedules', id, { status });
    closeModal();
    renderSchedules();
    updateDashboard();
    showToast(`일정이 "${statusText}"로 변경되었습니다`);
}

function deleteSchedule(id) {
    if (confirm('이 일정을 삭제하시겠습니까?')) {
        DB.remove('schedules', id);
        closeModal();
        renderSchedules();
        updateDashboard();
        showToast('일정이 삭제되었습니다');
    }
}

function filterSchedules(type, btn) {
    document.querySelectorAll('.filter-tab').forEach(t => t.classList.remove('active'));
    btn.classList.add('active');
    renderSchedules(type);
}
