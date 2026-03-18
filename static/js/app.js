// app.js - 前端交互逻辑

const API_BASE = '/api';

// 加载概览数据
async function loadOverview() {
    try {
        // 获取本周统计
        const now = new Date();
        const weekStart = new Date(now);
        weekStart.setDate(now.getDate() - now.getWeekday());
        const weekEnd = new Date(weekStart);
        weekEnd.setDate(weekStart.getDate() + 6);

        const statsRes = await fetch(`${API_BASE}/statistics?start_date=${formatDate(weekStart)}&end_date=${formatDate(weekEnd)}`);
        const statsData = await statsRes.json();

        const stats = statsData.statistics || [];
        
        // 更新统计卡片
        const study = stats.find(s => s.code === 'study');
        const play = stats.find(s => s.code === 'play');
        const sleep = stats.find(s => s.code === 'sleep');

        document.getElementById('week-study').textContent = study ? study.hours + 'h' : '0h';
        document.getElementById('week-play').textContent = play ? play.hours + 'h' : '0h';
        document.getElementById('week-sleep').textContent = sleep ? sleep.hours + 'h' : '0h';

        // 获取待处理文件数
        const filesRes = await fetch(`${API_BASE}/files/pending`);
        const filesData = await filesRes.json();
        document.getElementById('pending-files').textContent = (filesData.files || []).length;

        // 加载分类树
        loadCategoryTree();

    } catch (error) {
        console.error('加载概览失败:', error);
    }
}

// 加载分类树
async function loadCategoryTree() {
    try {
        const res = await fetch(`${API_BASE}/categories`);
        const data = await res.json();
        const container = document.getElementById('category-tree');
        
        if (data.categories && data.categories.length > 0) {
            container.innerHTML = renderTree(data.categories, 0);
        } else {
            container.innerHTML = '<div class="empty-state">暂无分类数据</div>';
        }
    } catch (error) {
        console.error('加载分类树失败:', error);
    }
}

// 渲染树状结构
function renderTree(categories, level) {
    let html = '';
    categories.forEach(cat => {
        const hasChildren = cat.children && cat.children.length > 0;
        html += `
            <div class="tree-node">
                <div class="tree-node-header" onclick="toggleNode(this)">
                    <span class="tree-toggle">${hasChildren ? '▶' : ''}</span>
                    <span class="tree-name">${cat.name}</span>
                    <span class="tree-hours" id="hours-${cat.id}"></span>
                </div>
                ${hasChildren ? `<div class="tree-children">${renderTree(cat.children, level + 1)}</div>` : ''}
            </div>
        `;
        
        // 加载该分类的时间
        loadCategoryHours(cat.id, cat.code);
    });
    return html;
}

// 加载分类时间
async function loadCategoryHours(categoryId, categoryCode) {
    try {
        const res = await fetch(`${API_BASE}/statistics/hierarchical?category_id=${categoryId}`);
        const data = await res.json();
        const hours = data[categoryCode]?.total_hours || 0;
        const el = document.getElementById(`hours-${categoryId}`);
        if (el) el.textContent = hours > 0 ? `${hours}h` : '';
    } catch (error) {
        console.error('加载时间失败:', error);
    }
}

// 切换节点展开
function toggleNode(header) {
    const children = header.nextElementSibling;
    if (children && children.classList.contains('tree-children')) {
        children.classList.toggle('expanded');
        const toggle = header.querySelector('.tree-toggle');
        if (toggle) toggle.textContent = children.classList.contains('expanded') ? '▼' : '▶';
    }
}

// 格式化日期
function formatDate(date) {
    return date.toISOString().split('T')[0];
}

// 获取URL参数
function getUrlParam(name) {
    const params = new URLSearchParams(window.location.search);
    return params.get(name);
}
