// ===== 자료 송부 & 계약서 초안 =====

function showSendMaterialForm(preselectedPropertyId) {
    const properties = DB.get('properties');
    const customers = DB.get('customers');

    const html = `
        <div class="modal-title">
            매물자료 송부
            <button class="modal-close" onclick="closeModal()">&times;</button>
        </div>
        <form onsubmit="sendMaterial(event)">
            <div class="form-group">
                <label class="form-label">매물 선택 *</label>
                <select class="form-select" id="sendProperty" required onchange="updateMaterialPreview()">
                    <option value="">선택하세요</option>
                    ${properties.map(p =>
                        `<option value="${p.id}" ${p.id === preselectedPropertyId ? 'selected' : ''}>${PROPERTY_TYPES[p.type]} - ${p.address} (${DEAL_TYPES[p.deal]})</option>`
                    ).join('')}
                </select>
            </div>
            <div class="form-group">
                <label class="form-label">받는 고객 *</label>
                <select class="form-select" id="sendCustomer" required>
                    <option value="">선택하세요</option>
                    ${customers.map(c =>
                        `<option value="${c.id}">${c.name} (${CUSTOMER_TYPES[c.type]}) - ${formatPhone(c.phone)}</option>`
                    ).join('')}
                </select>
            </div>
            <div class="form-group">
                <label class="form-label">송부 방법</label>
                <select class="form-select" id="sendMethod">
                    <option value="kakao">카카오톡</option>
                    <option value="sms">문자메시지</option>
                </select>
            </div>
            <div class="form-group">
                <label class="form-label">미리보기</label>
                <div class="preview-box" id="materialPreview">매물을 선택하면 미리보기가 표시됩니다</div>
            </div>
            <div class="form-actions">
                <button type="button" class="btn btn-outline btn-full" onclick="closeModal()">취소</button>
                <button type="submit" class="btn btn-primary btn-full">복사하기</button>
            </div>
        </form>
    `;
    openModal(html);

    if (preselectedPropertyId) {
        setTimeout(() => updateMaterialPreview(), 100);
    }
}

function updateMaterialPreview() {
    const propId = document.getElementById('sendProperty').value;
    const preview = document.getElementById('materialPreview');

    if (!propId) {
        preview.textContent = '매물을 선택하면 미리보기가 표시됩니다';
        return;
    }

    const p = DB.findById('properties', propId);
    if (!p) return;

    const priceText = p.deal === 'monthly'
        ? `보증금 ${formatPrice(p.price)} / 월 ${formatPrice(p.rent)}`
        : `${DEAL_TYPES[p.deal]} ${formatPrice(p.price)}`;

    const text = [
        `[매물 안내]`,
        ``,
        `${PROPERTY_TYPES[p.type]} ${DEAL_TYPES[p.deal]}`,
        `위치: ${p.address}${p.addressDetail ? ' ' + p.addressDetail : ''}`,
        `가격: ${priceText}`,
        p.size ? `면적: ${p.size}평` : '',
        p.floor ? `층수: ${p.floor}` : '',
        p.memo ? `특징: ${p.memo}` : '',
        ``,
        `문의: 중개편리앱`,
        `방문 예약은 연락 부탁드립니다.`
    ].filter(Boolean).join('\n');

    preview.textContent = text;
}

function sendMaterial(e) {
    e.preventDefault();
    const propId = document.getElementById('sendProperty').value;
    const custId = document.getElementById('sendCustomer').value;
    const method = document.getElementById('sendMethod').value;
    const previewText = document.getElementById('materialPreview').textContent;

    // 송부 이력 저장
    DB.add('sendHistory', {
        type: 'material',
        propertyId: propId,
        customerId: custId,
        method: method,
        content: previewText
    });

    // 클립보드에 복사
    navigator.clipboard.writeText(previewText).then(() => {
        closeModal();
        showToast('매물자료가 클립보드에 복사되었습니다!\n카카오톡/문자에 붙여넣기 해주세요');
    }).catch(() => {
        // 클립보드 실패 시 대체 방법
        const textarea = document.createElement('textarea');
        textarea.value = previewText;
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand('copy');
        textarea.remove();
        closeModal();
        showToast('매물자료가 복사되었습니다!');
    });
}

// ===== 계약서 초안 =====

function showContractDraftForm() {
    const properties = DB.get('properties');
    const customers = DB.get('customers');

    const html = `
        <div class="modal-title">
            계약서 초안 작성
            <button class="modal-close" onclick="closeModal()">&times;</button>
        </div>
        <form onsubmit="generateContractDraft(event)">
            <div class="form-group">
                <label class="form-label">계약유형 *</label>
                <select class="form-select" id="contractType" required>
                    <option value="">선택하세요</option>
                    <option value="sale">매매계약서</option>
                    <option value="jeonse">전세계약서</option>
                    <option value="monthly">월세계약서</option>
                </select>
            </div>
            <div class="form-group">
                <label class="form-label">매물 선택</label>
                <select class="form-select" id="contractProperty" onchange="autoFillContract()">
                    <option value="">선택하세요</option>
                    ${properties.map(p =>
                        `<option value="${p.id}">${PROPERTY_TYPES[p.type]} - ${p.address}</option>`
                    ).join('')}
                </select>
            </div>
            <div class="form-group">
                <label class="form-label">매도인/임대인</label>
                <select class="form-select" id="contractSeller">
                    <option value="">선택하세요</option>
                    ${customers.filter(c => c.type === 'seller').map(c =>
                        `<option value="${c.id}">${c.name}</option>`
                    ).join('')}
                </select>
            </div>
            <div class="form-group">
                <label class="form-label">매수인/임차인</label>
                <select class="form-select" id="contractBuyer">
                    <option value="">선택하세요</option>
                    ${customers.filter(c => c.type === 'buyer' || c.type === 'tenant').map(c =>
                        `<option value="${c.id}">${c.name} (${CUSTOMER_TYPES[c.type]})</option>`
                    ).join('')}
                </select>
            </div>
            <div class="form-group">
                <label class="form-label">소재지</label>
                <input type="text" class="form-input" id="contractAddress" placeholder="부동산 소재지">
            </div>
            <div class="form-row">
                <div class="form-group">
                    <label class="form-label">금액(만원)</label>
                    <input type="number" class="form-input" id="contractPrice" placeholder="50000">
                </div>
                <div class="form-group">
                    <label class="form-label">계약금(만원)</label>
                    <input type="number" class="form-input" id="contractDeposit" placeholder="5000">
                </div>
            </div>
            <div class="form-row">
                <div class="form-group">
                    <label class="form-label">중도금(만원)</label>
                    <input type="number" class="form-input" id="contractMid" placeholder="20000">
                </div>
                <div class="form-group">
                    <label class="form-label">잔금(만원)</label>
                    <input type="number" class="form-input" id="contractBalance" placeholder="25000">
                </div>
            </div>
            <div class="form-group">
                <label class="form-label">잔금일</label>
                <input type="date" class="form-input" id="contractBalanceDate">
            </div>
            <div class="form-group">
                <label class="form-label">특약사항</label>
                <textarea class="form-textarea" id="contractSpecial" placeholder="특약사항을 입력하세요"></textarea>
            </div>
            <div class="form-actions">
                <button type="button" class="btn btn-outline btn-full" onclick="closeModal()">취소</button>
                <button type="submit" class="btn btn-primary btn-full">초안 생성</button>
            </div>
        </form>
    `;
    openModal(html);
}

function autoFillContract() {
    const propId = document.getElementById('contractProperty').value;
    if (!propId) return;

    const p = DB.findById('properties', propId);
    if (!p) return;

    document.getElementById('contractAddress').value = p.address + (p.addressDetail ? ' ' + p.addressDetail : '');
    document.getElementById('contractPrice').value = p.price || '';
    if (p.ownerId) {
        document.getElementById('contractSeller').value = p.ownerId;
    }

    const typeMap = { sale: 'sale', jeonse: 'jeonse', monthly: 'monthly' };
    document.getElementById('contractType').value = typeMap[p.deal] || '';
}

function generateContractDraft(e) {
    e.preventDefault();

    const contractType = document.getElementById('contractType').value;
    const sellerId = document.getElementById('contractSeller').value;
    const buyerId = document.getElementById('contractBuyer').value;
    const address = document.getElementById('contractAddress').value;
    const price = document.getElementById('contractPrice').value;
    const deposit = document.getElementById('contractDeposit').value;
    const mid = document.getElementById('contractMid').value;
    const balance = document.getElementById('contractBalance').value;
    const balanceDate = document.getElementById('contractBalanceDate').value;
    const special = document.getElementById('contractSpecial').value;

    const seller = sellerId ? DB.findById('customers', sellerId) : null;
    const buyer = buyerId ? DB.findById('customers', buyerId) : null;

    const typeNames = { sale: '부동산 매매', jeonse: '부동산 전세', monthly: '부동산 월세' };
    const sellerLabel = contractType === 'sale' ? '매도인' : '임대인';
    const buyerLabel = contractType === 'sale' ? '매수인' : '임차인';
    const priceLabel = contractType === 'sale' ? '매매대금' : contractType === 'jeonse' ? '보증금' : '보증금';

    const today = new Date();
    const todayStr = `${today.getFullYear()}년 ${today.getMonth() + 1}월 ${today.getDate()}일`;

    const draftText = [
        `${typeNames[contractType]} 계약서 (초안)`,
        ``,
        `1. 부동산의 표시`,
        `   소재지: ${address || '___________________'}`,
        ``,
        `2. 계약 내용`,
        `   ${priceLabel}: ${price ? formatPrice(price) : '___________'}`,
        `   계약금: ${deposit ? formatPrice(deposit) : '___________'} (계약 시 지급)`,
        mid ? `   중도금: ${formatPrice(mid)}` : '',
        `   잔  금: ${balance ? formatPrice(balance) : '___________'} (${balanceDate ? formatDate(balanceDate) : '____년 __월 __일'} 지급)`,
        ``,
        `3. ${sellerLabel}과 ${buyerLabel}은 위 부동산에 대하여`,
        `   위와 같이 계약을 체결하고 이를 성실히 이행할 것을 약정합니다.`,
        special ? `\n4. 특약사항\n   ${special}` : '',
        ``,
        `계약일: ${todayStr}`,
        ``,
        `${sellerLabel}: ${seller ? seller.name : '___________'} (인)`,
        `  연락처: ${seller ? formatPhone(seller.phone) : '_______________'}`,
        ``,
        `${buyerLabel}: ${buyer ? buyer.name : '___________'} (인)`,
        `  연락처: ${buyer ? formatPhone(buyer.phone) : '_______________'}`,
        ``,
        `개업공인중개사: ___________ (인)`,
        `사무소명: _______________`,
        `등록번호: _______________`
    ].filter(line => line !== '').join('\n');

    // 계약서 저장
    DB.add('contracts', {
        type: contractType,
        sellerId,
        buyerId,
        address,
        price,
        content: draftText,
        propertyId: document.getElementById('contractProperty').value
    });

    // 미리보기로 전환
    closeModal();

    const previewHtml = `
        <div class="modal-title">
            계약서 초안
            <button class="modal-close" onclick="closeModal()">&times;</button>
        </div>
        <div class="preview-box" style="font-family:monospace;line-height:2;">${draftText.replace(/\n/g, '<br>')}</div>
        <div class="form-actions">
            <button class="btn btn-primary btn-full" onclick="copyContract()">복사하기</button>
        </div>
        <p style="text-align:center;color:var(--gray-400);font-size:12px;margin-top:12px;">
            * 이 초안은 참고용이며, 실제 계약 시 공인중개사협회 표준계약서를 사용하세요
        </p>
    `;

    // 전역에 저장
    window._lastContractDraft = draftText;
    openModal(previewHtml);
    updateDashboard();
}

function copyContract() {
    const text = window._lastContractDraft;
    navigator.clipboard.writeText(text).then(() => {
        showToast('계약서 초안이 복사되었습니다!');
    }).catch(() => {
        const textarea = document.createElement('textarea');
        textarea.value = text;
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand('copy');
        textarea.remove();
        showToast('계약서 초안이 복사되었습니다!');
    });
}

// ===== 송부 내역 =====

function showSendHistory() {
    const history = DB.get('sendHistory');
    const contracts = DB.get('contracts');
    const content = document.getElementById('documentContent');

    if (history.length === 0 && contracts.length === 0) {
        content.innerHTML = '<div class="empty-state">송부 내역이 없습니다</div>';
        return;
    }

    let html = '<div class="section-title" style="margin-top:16px;">자료 송부 내역</div>';

    if (history.length === 0) {
        html += '<div class="empty-state">송부 내역이 없습니다</div>';
    } else {
        html += history.map(h => {
            const customer = h.customerId ? DB.findById('customers', h.customerId) : null;
            const property = h.propertyId ? DB.findById('properties', h.propertyId) : null;
            const methodText = h.method === 'kakao' ? '카카오톡' : '문자';
            return `
                <div class="list-item">
                    <div class="list-item-header">
                        <span class="list-item-name">${customer?.name || '알수없음'}</span>
                        <span class="badge badge-viewing">${methodText}</span>
                    </div>
                    <div class="list-item-sub">${property ? property.address : ''}</div>
                    <div class="list-item-sub">${formatDate(h.createdAt?.split('T')[0])}</div>
                </div>
            `;
        }).join('');
    }

    html += '<div class="section-title" style="margin-top:24px;">계약서 초안 내역</div>';

    if (contracts.length === 0) {
        html += '<div class="empty-state">작성된 계약서가 없습니다</div>';
    } else {
        html += contracts.map(c => {
            const typeNames = { sale: '매매', jeonse: '전세', monthly: '월세' };
            const seller = c.sellerId ? DB.findById('customers', c.sellerId) : null;
            const buyer = c.buyerId ? DB.findById('customers', c.buyerId) : null;
            return `
                <div class="list-item" onclick="viewSavedContract('${c.id}')">
                    <div class="list-item-header">
                        <span class="list-item-name">${typeNames[c.type]} 계약서</span>
                        <span class="badge badge-contract">${formatDate(c.createdAt?.split('T')[0])}</span>
                    </div>
                    <div class="list-item-sub">${c.address || ''}</div>
                    <div class="list-item-sub">${seller?.name || ''} / ${buyer?.name || ''}</div>
                </div>
            `;
        }).join('');
    }

    content.innerHTML = html;
}

function viewSavedContract(id) {
    const c = DB.findById('contracts', id);
    if (!c) return;

    window._lastContractDraft = c.content;
    const html = `
        <div class="modal-title">
            계약서 초안
            <button class="modal-close" onclick="closeModal()">&times;</button>
        </div>
        <div class="preview-box" style="font-family:monospace;line-height:2;">${c.content.replace(/\n/g, '<br>')}</div>
        <div class="form-actions">
            <button class="btn btn-primary btn-full" onclick="copyContract()">복사하기</button>
        </div>
    `;
    openModal(html);
}
