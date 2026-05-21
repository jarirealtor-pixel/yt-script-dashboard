// ===== 매물 관리 =====

function showPropertyForm(editId) {
    const prop = editId ? DB.findById('properties', editId) : null;
    const title = prop ? '매물 정보 수정' : '매물 등록';
    const customers = DB.get('customers').filter(c => c.type === 'seller');

    const html = `
        <div class="modal-title">
            ${title}
            <button class="modal-close" onclick="closeModal()">&times;</button>
        </div>
        <form onsubmit="saveProperty(event, '${editId || ''}')">
            <div class="form-group">
                <label class="form-label">매물종류 *</label>
                <select class="form-select" id="propType" required>
                    <option value="">선택하세요</option>
                    ${Object.entries(PROPERTY_TYPES).map(([k, v]) =>
                        `<option value="${k}" ${prop?.type === k ? 'selected' : ''}>${v}</option>`
                    ).join('')}
                </select>
            </div>
            <div class="form-group">
                <label class="form-label">거래유형 *</label>
                <select class="form-select" id="propDeal" required>
                    <option value="">선택하세요</option>
                    <option value="sale" ${prop?.deal === 'sale' ? 'selected' : ''}>매매</option>
                    <option value="jeonse" ${prop?.deal === 'jeonse' ? 'selected' : ''}>전세</option>
                    <option value="monthly" ${prop?.deal === 'monthly' ? 'selected' : ''}>월세</option>
                </select>
            </div>
            <div class="form-group">
                <label class="form-label">주소 *</label>
                <input type="text" class="form-input" id="propAddress" required
                    value="${prop?.address || ''}" placeholder="서울시 강남구 역삼동 123-45">
            </div>
            <div class="form-group">
                <label class="form-label">상세주소</label>
                <input type="text" class="form-input" id="propAddressDetail"
                    value="${prop?.addressDetail || ''}" placeholder="○○아파트 101동 1001호">
            </div>
            <div class="form-row">
                <div class="form-group">
                    <label class="form-label">면적(평)</label>
                    <input type="text" class="form-input" id="propSize"
                        value="${prop?.size || ''}" placeholder="32">
                </div>
                <div class="form-group">
                    <label class="form-label">층수</label>
                    <input type="text" class="form-input" id="propFloor"
                        value="${prop?.floor || ''}" placeholder="10/25층">
                </div>
            </div>
            <div class="form-row">
                <div class="form-group">
                    <label class="form-label">가격(만원) *</label>
                    <input type="number" class="form-input" id="propPrice" required
                        value="${prop?.price || ''}" placeholder="50000">
                </div>
                <div class="form-group" id="monthlyRentGroup" style="display:none">
                    <label class="form-label">월세(만원)</label>
                    <input type="number" class="form-input" id="propRent"
                        value="${prop?.rent || ''}" placeholder="100">
                </div>
            </div>
            <div class="form-group">
                <label class="form-label">매도인/임대인</label>
                <select class="form-select" id="propOwner">
                    <option value="">선택하세요</option>
                    ${customers.map(c =>
                        `<option value="${c.id}" ${prop?.ownerId === c.id ? 'selected' : ''}>${c.name} (${formatPhone(c.phone)})</option>`
                    ).join('')}
                </select>
                <small style="color:var(--gray-400);font-size:11px;margin-top:4px;display:block;">
                    고객관리에서 매도인으로 먼저 등록하세요
                </small>
            </div>
            <div class="form-group">
                <label class="form-label">특징/메모</label>
                <textarea class="form-textarea" id="propMemo" placeholder="남향, 리모델링 완료, 주차 2대 등">${prop?.memo || ''}</textarea>
            </div>
            <div class="form-actions">
                <button type="button" class="btn btn-outline btn-full" onclick="closeModal()">취소</button>
                <button type="submit" class="btn btn-primary btn-full">저장</button>
            </div>
        </form>
    `;
    openModal(html);

    // 월세 선택 시 월세 입력란 표시
    setTimeout(() => {
        const dealSelect = document.getElementById('propDeal');
        const rentGroup = document.getElementById('monthlyRentGroup');
        function toggleRent() {
            rentGroup.style.display = dealSelect.value === 'monthly' ? 'block' : 'none';
        }
        dealSelect.addEventListener('change', toggleRent);
        toggleRent();
    }, 100);
}

function saveProperty(e, editId) {
    e.preventDefault();
    const data = {
        type: document.getElementById('propType').value,
        deal: document.getElementById('propDeal').value,
        address: document.getElementById('propAddress').value.trim(),
        addressDetail: document.getElementById('propAddressDetail').value.trim(),
        size: document.getElementById('propSize').value.trim(),
        floor: document.getElementById('propFloor').value.trim(),
        price: document.getElementById('propPrice').value,
        rent: document.getElementById('propRent').value,
        ownerId: document.getElementById('propOwner').value,
        memo: document.getElementById('propMemo').value.trim()
    };

    if (editId) {
        DB.update('properties', editId, data);
        showToast('매물 정보가 수정되었습니다');
    } else {
        DB.add('properties', data);
        showToast('매물이 등록되었습니다');
    }

    closeModal();
    renderProperties();
    updateDashboard();
}

function renderProperties(filter) {
    let properties = DB.get('properties');
    if (filter) {
        const q = filter.toLowerCase();
        properties = properties.filter(p =>
            p.address.toLowerCase().includes(q) ||
            PROPERTY_TYPES[p.type]?.includes(q) ||
            DEAL_TYPES[p.deal]?.includes(q)
        );
    }

    const container = document.getElementById('propertyList');
    if (properties.length === 0) {
        container.innerHTML = '<div class="empty-state">등록된 매물이 없습니다<br><small>위의 \'매물 등록\' 버튼을 눌러주세요</small></div>';
        return;
    }

    container.innerHTML = properties.map(p => {
        const priceText = p.deal === 'monthly'
            ? `보증금 ${formatPrice(p.price)} / 월 ${formatPrice(p.rent)}`
            : formatPrice(p.price);

        return `
            <div class="list-item" onclick="showPropertyDetail('${p.id}')">
                <div class="list-item-header">
                    <span class="list-item-name">${PROPERTY_TYPES[p.type]}</span>
                    <span class="badge badge-${p.deal}">${DEAL_TYPES[p.deal]}</span>
                </div>
                <div class="list-item-sub">${p.address}</div>
                <div class="list-item-sub" style="font-weight:600;color:var(--gray-800);">${priceText}</div>
                ${p.size ? `<div class="list-item-sub">${p.size}평 ${p.floor ? '/ ' + p.floor : ''}</div>` : ''}
            </div>
        `;
    }).join('');
}

function showPropertyDetail(id) {
    const p = DB.findById('properties', id);
    if (!p) return;

    const owner = p.ownerId ? DB.findById('customers', p.ownerId) : null;
    const priceText = p.deal === 'monthly'
        ? `보증금 ${formatPrice(p.price)} / 월 ${formatPrice(p.rent)}`
        : formatPrice(p.price);

    const html = `
        <div class="modal-title">
            매물 상세
            <button class="modal-close" onclick="closeModal()">&times;</button>
        </div>
        <div class="detail-section">
            <div class="detail-row">
                <span class="detail-label">매물종류</span>
                <span class="detail-value">${PROPERTY_TYPES[p.type]} <span class="badge badge-${p.deal}">${DEAL_TYPES[p.deal]}</span></span>
            </div>
            <div class="detail-row">
                <span class="detail-label">주소</span>
                <span class="detail-value">${p.address} ${p.addressDetail || ''}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">가격</span>
                <span class="detail-value" style="font-weight:700">${priceText}</span>
            </div>
            ${p.size ? `<div class="detail-row"><span class="detail-label">면적</span><span class="detail-value">${p.size}평</span></div>` : ''}
            ${p.floor ? `<div class="detail-row"><span class="detail-label">층수</span><span class="detail-value">${p.floor}</span></div>` : ''}
            ${owner ? `<div class="detail-row"><span class="detail-label">매도인</span><span class="detail-value">${owner.name} (${formatPhone(owner.phone)})</span></div>` : ''}
            ${p.memo ? `<div class="detail-row"><span class="detail-label">특징</span><span class="detail-value">${p.memo}</span></div>` : ''}
        </div>
        <div class="form-actions">
            <button class="btn btn-success btn-full" onclick="closeModal();showSendMaterialForm('${p.id}')">자료 송부</button>
        </div>
        <div class="form-actions">
            <button class="btn btn-outline btn-full" onclick="showPropertyForm('${p.id}')">수정</button>
            <button class="btn btn-danger btn-full" onclick="deleteProperty('${p.id}')">삭제</button>
        </div>
    `;
    openModal(html);
}

function deleteProperty(id) {
    if (confirm('이 매물을 삭제하시겠습니까?')) {
        DB.remove('properties', id);
        closeModal();
        renderProperties();
        updateDashboard();
        showToast('매물이 삭제되었습니다');
    }
}

function filterProperties() {
    const query = document.getElementById('propertySearch').value;
    renderProperties(query);
}
