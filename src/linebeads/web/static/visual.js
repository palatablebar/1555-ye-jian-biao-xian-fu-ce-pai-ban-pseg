function renderVisual(target, data) {
    const bySegment = new Map();
    for (const row of data.rows) {
        if (!bySegment.has(row.zone)) bySegment.set(row.zone,[]);
        bySegment.get(row.zone).push(row);
    }
    const board = node('div',undefined,'depots-list');
    for (const [lane,tickets] of bySegment) {
        const slots = tickets.filter(item => item.state === '已分派').reduce((sum,row) => sum+row.cost,0);
        const peak = Math.max(...tickets.map(item => item.estimate));
        const gauge = node('meter');
        gauge.max = data.capacity;
        gauge.value = slots;
        gauge.setAttribute('aria-label',`${lane}使用${slots}个工位`);
        const cell = node('div',undefined,'depot');
        cell.append(node('h3',lane),gauge,node('small',`${slots} 工位 · 峰值衰减 ${format.format(peak)}`));
        board.append(cell);
    }
    target.append(board);
}
