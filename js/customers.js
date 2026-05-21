// ===== 고객 관리 =====

function showCustomerForm(editId) {
    const customer = editId ? DB.findById('customers', editId) : null;
    const title = customer ? '고객 정보 수정' : '고객 등록';

    const html = `
        <div class="modal-title">
            ${title}
            <button class="modal-close" onclick="closeModal()">&times;</button>
        </div>
        <form onsubmit="saveCustomer(event, '${editId || ''}')">
            <div class="form-group">
                <label class="form-label">고객명 *</label>
                <input type="text" class="form-input" id="custName" required
                    value="${customer?.name || ''}" placeholder="홍길동">
            </div>
            <div class="form-group">
                <label class="form-label">연락처 *</label>
                <input type="tel" class="form-input" id="custPhone" required
                    value="${customer?.phone || ''}" placeholder="010-1234-5678">
            </div>
            <div class="form-group">
                <label class="form-label">고객유형 *</label>
                <select class="form-select" id="custType" required>
                    <option value="">선택하세요</option>
                    <option value="buyer" ${customer?.type === 'buyer' ? 'selected' : ''}>매수인</option>
                    <option value="seller" ${customer?.type === 'seller' ? 'selected' : ''}>매도인</option>
                    <option value="tenant" ${customer?.type === 'tenant' ? 'selected' : ''}>세입자</option>
                    <option value="agent" ${customer?.type === 'agent' ? 'selected' : ''}>참여중개사</option>
                </select>
            </div>
            <div class="form-group">
                <label class="form-label">관심지역</label>
                <input type="text" class="form-input" id="custArea"
                    value="${customer?.area || ''}" placeholder="강남구, 서초구 등">
            </div>
            <div class="form-group">
                <label class="form-label">희망매물</label>
                <input type="text" class="form-input" id="custWant"
                    value="${customer?.want || ''}" placeholder="아파트 30평대, 전세 등">
            </div>
            <div class="form-group">
                <label class="form-label">예산</label>
                <input type="text" class="form-input" id="custBudget"
                    value="${customer?.budget || ''}" placeholder="예: 50000 (만원 단위)">
            </div>
            <div class="form-group">
                <label class="form-label">메모</label>
                <textarea class="form-textarea" id="custMemo" placeholder="특이사항, 요청사항 등">${customer?.memo || ''}</textarea>
            </div>
            <div class="form-actions">
                <button type="button" class="btn btn-outline btn-full" onclick="closeModal()">취소</button>
                <button type="submit" class="btn btn-primary btn-full">저장</button>
            </div>
        </form>
    `;
    openModal(html);
}

function saveCustomer(e, editId) {
    e.preventDefault();
    const data = {
        name: document.getElementById('custName').value.trim(),
        phone: document.getElementById('custPhone').value.trim(),
        type: document.getElementById('custType').value,
        area: document.getElementById('custArea').value.trim(),
        want: document.getElementById('custWant').value.trim(),
        budget: document.getElementById('custBudget').value.trim(),
        memo: document.getElementById('custMemo').value.trim()
    };

    if (editId) {
        DB.update('customers', editId, data);
        showToast('고객 정보가 수정되었습니다');
    } else {
        DB.add('customers', data);
        showToast('고객이 등록되었습니다');
    }

    closeModal();
    renderCustomers();
    updateDashboard();
}

function renderCustomers(filter) {
    let customers = DB.get('customers');
    if (filter) {
        const q = filter.toLowerCase();
        customers = customers.filter(c =>
            c.name.toLowerCase().includes(q) ||
            c.phone.includes(q)
        );
    }

    const container = document.getElementById('customerList');
    if (customers.length === 0) {
        container.innerHTML = '<div class="empty-state">등록된 고객이 없습니다<br><small>위의 \'고객 등록\' 버튼을 눌러주세요</small></div>';
        return;
    }

    container.innerHTML = customers.map(c => `
        <div class="list-item" onclick="showCustomerDetail('${c.id}')">
            <div class="list-item-header">
                <span class="list-item-name">${c.name}</span>
                <span class="badge badge-${c.type}">${CUSTOMER_TYPES[c.type]}</span>
            </div>
            <div class="list-item-sub">${formatPhone(c.phone)}</div>
            ${c.area ? `<div class="list-item-sub">관심: ${c.area}</div>` : ''}
        </div>
    `).join('');
}

function showCustomerDetail(id) {
    const c = DB.findById('customers', id);
    if (!c) return;

    const schedules = DB.get('schedules').filter(s => s.customerId === id);

    const html = `
        <div class="modal-title">
            고객 상세
            <button class="modal-close" onclick="closeModal()">&times;</button>
        </div>
        <div class="detail-section">
            <div class="detail-row">
                <span class="detail-label">이름</span>
                <span class="detail-value">${c.name} <span class="badge badge-${c.type}">${CUSTOMER_TYPES[c.type]}</span></span>
            </div>
            <div class="detail-row">
                <span class="detail-label">연락처</span>
                <span class="detail-value">${formatPhone(c.phone)}</span>
            </div>
            ${c.area ? `<div class="detail-row"><span class="detail-label">관심지역</span><span class="detail-value">${c.area}</span></div>` : ''}
            ${c.want ? `<div class="detail-row"><span class="detail-label">희망매물</span><span class="detail-value">${c.want}</span></div>` : ''}
            ${c.budget ? `<div class="detail-row"><span class="detail-label">예산</span><span class="detail-value">${formatPrice(c.budget)}</span></div>` : ''}
            ${c.memo ? `<div class="detail-row"><span class="detail-label">메모</span><span class="detail-value">${c.memo}</span></div>` : ''}
        </div>

        ${schedules.length > 0 ? `
            <div class="section-title">관련 일정</div>
            ${schedules.map(s => `
                <div class="list-item">
                    <div class="list-item-header">
                        <span class="list-item-name">${formatDateTime(s.date, s.time)}</span>
                        <span class="badge badge-${s.type}">${SCHEDULE_TYPES[s.type]}</span>
                    </div>
                    <div class="list-item-sub">${s.title}</div>
                </div>
            `).join('')}
        ` : ''}

        <div class="form-actions">
            <button class="btn btn-outline btn-full" onclick="showCustomerForm('${c.id}')">수정</button>
            <button class="btn btn-danger btn-full" onclick="deleteCustomer('${c.id}')">삭제</button>
        </div>
    `;
    openModal(html);
}

function deleteCustomer(id) {
    if (confirm('이 고객을 삭제하시겠습니까?')) {
        DB.remove('customers', id);
        closeModal();
        renderCustomers();
        updateDashboard();
        showToast('고객이 삭제되었습니다');
    }
}

function filterCustomers() {
    const query = document.getElementById('customerSearch').value;
    renderCustomers(query);
}
