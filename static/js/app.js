// app.js - 前端交互逻辑

const API_BASE = '/api';

let pieChart = null;
let currentRootId = null; // 当前根节点ID
let currentRootName = '';  // 当前根节点名称
let currentStartDate = null;
let currentEndDate = null;

function initOverview() {
    pieChart = echarts.init(document.getElementById('pie-chart'));
    pieChart.on('click', handlePieClick);
    loadTimeline();
    loadCategoryTree();
    loadPieData();
    
    window.addEventListener('resize', () => {
        if (pieChart) pieChart.resize();
    });
}

function handlePieClick(params) {
    const data = params.data;
    if (data && data.id) {
        navigateToCategory(data.id, data.name);
    }
}

async function loadTimeline() {
    const granularity = document.getElementById('time-granularity').value;
    try {
        const res = await fetch(`${API_BASE}/timeline/dates?granularity=${granularity}`);
        const data = await res.json();
        renderTimeline(data.dates || []);
    } catch (error) {
        console.error('加载时间线失败:', error);
    }
}

function renderTimeline(dates) {
    const container = document.getElementById('timeline');
    if (dates.length === 0) {
        container.innerHTML = '<div class="empty-state">暂无数据</div>';
        return;
    }
    
    let html = '<div class="timeline-items">';
    dates.forEach((date, index) => {
        html += `<div class="timeline-item ${index === 0 ? 'active' : ''}" data-date="${date}" onclick="selectTimelineDate('${date}', this)">${date}</div>`;
    });
    html += '</div>';
    container.innerHTML = html;
    
    if (dates.length > 0) {
        selectTimelineDate(dates[0], container.querySelector('.timeline-item'));
    }
}

function selectTimelineDate(date, element) {
    document.querySelectorAll('.timeline-item').forEach(el => el.classList.remove('active'));
    element.classList.add('active');
    
    const granularity = document.getElementById('time-granularity').value;
    
    if (granularity === 'year') {
        currentStartDate = `${date}-01-01`;
        currentEndDate = `${date}-12-31`;
    } else if (granularity === 'month') {
        const [year, month] = date.split('-');
        const lastDay = new Date(year, month, 0).getDate();
        currentStartDate = `${year}-${month}-01`;
        currentEndDate = `${year}-${month}-${lastDay}`;
    } else {
        const [year, week] = date.split('-W');
        const firstDay = new Date(year, 0, 1 + (parseInt(week) - 1) * 7);
        const lastDay = new Date(firstDay);
        lastDay.setDate(lastDay.getDate() + 6);
        currentStartDate = formatDate(firstDay);
        currentEndDate = formatDate(lastDay);
    }
    
    // 重置到根节点
    currentRootId = null;
    currentRootName = '';
    
    loadPieData();
    loadCategoryTree();
}

document.getElementById('time-granularity').addEventListener('change', loadTimeline);

async function loadPieData() {
    try {
        let url;
        
        if (currentRootId) {
            // 当前有选中的根节点，显示其子节点
            url = `${API_BASE}/statistics/by-category?category_id=${currentRootId}`;
        } else {
            // 默认显示Level 0
            url = `${API_BASE}/statistics/by-level?level=0`;
        }
        
        if (currentStartDate && currentEndDate) {
            url += `&start_date=${currentStartDate}&end_date=${currentEndDate}`;
        }
        
        const res = await fetch(url);
        const data = await res.json();
        renderPieChart(data.statistics || []);
    } catch (error) {
        console.error('加载饼图数据失败:', error);
    }
}

function renderPieChart(data) {
    if (!pieChart) return;
    
    if (data.length === 0) {
        pieChart.setOption({
            title: { text: '暂无数据', left: 'center', top: 'center' },
            series: []
        });
        return;
    }
    
    const option = {
        tooltip: {
            trigger: 'item',
            formatter: '{b}: {c}h ({d}%)'
        },
        series: [
            {
                type: 'pie',
                radius: ['40%', '70%'],
                avoidLabelOverlap: true,
                itemStyle: {
                    borderRadius: 10,
                    borderColor: '#fff',
                    borderWidth: 2
                },
                label: {
                    show: true,
                    formatter: '{b}: {c}h'
                },
                emphasis: {
                    label: {
                        show: true,
                        fontSize: 16,
                        fontWeight: 'bold'
                    }
                },
                data: data.map(item => ({
                    name: item.name,
                    value: item.hours,
                    id: item.id,
                    level: item.level,
                    itemStyle: getColor(item.level)
                }))
            }
        ]
    };
    
    pieChart.setOption(option);
}

function getColor(level) {
    const colors = [
        '#5470c6', '#91cc75', '#fac858', '#ee6666', 
        '#73c0de', '#3ba272', '#fc8452', '#9a60b4'
    ];
    return { color: colors[level % colors.length] };
}

async function loadCategoryTree() {
    try {
        const res = await fetch(`${API_BASE}/categories`);
        const data = await res.json();
        const container = document.getElementById('category-tree');
        
        if (data.categories && data.categories.length > 0) {
            renderTreeView(data.categories, container);
        } else {
            container.innerHTML = '<div class="empty-state">暂无分类数据</div>';
        }
    } catch (error) {
        console.error('加载分类树失败:', error);
    }
}

function renderTreeView(allCategories, container) {
    // 找到当前根节点
    let rootCategories = allCategories;
    let rootCategory = null;
    
    if (currentRootId) {
        for (const cat of allCategories) {
            if (cat.id === currentRootId) {
                rootCategory = cat;
                rootCategories = cat.children || [];
                break;
            }
            // 递归查找
            if (cat.children) {
                const found = findCategoryInTree(cat.children, currentRootId);
                if (found) {
                    rootCategory = found;
                    rootCategories = found.children || [];
                    break;
                }
            }
        }
    }
    
    // 构建HTML
    let html = '<div class="tree-container">';
    
    // 返回按钮（如果有根节点）
    if (currentRootId) {
        html += `<div class="tree-back-btn" onclick="goBack()" title="返回上一层">↑</div>`;
    }
    
    // 根节点
    if (currentRootId && rootCategory) {
        html += `
            <div class="tree-root" onclick="onRootClick()">
                ${currentRootName || rootCategory.name}
            </div>
        `;
    }
    
    // 连接箭头
    if (rootCategories.length > 0) {
        html += '<div class="tree-arrow-line">';
        rootCategories.forEach(() => {
            html += '<div class="tree-arrow-down">↓</div>';
        });
        html += '</div>';
    }
    
    // 子节点
    if (rootCategories.length > 0) {
        html += '<div class="tree-children">';
        rootCategories.forEach(cat => {
            const hasChildren = cat.children && cat.children.length > 0;
            const label = hasChildren ? `${cat.name} →` : cat.name;
            html += `
                <div class="tree-node" onclick="navigateToCategory(${cat.id}, '${cat.name}')">
                    ${label}
                </div>
            `;
        });
        html += '</div>';
    } else if (currentRootId) {
        html += '<div class="tree-empty">无子节点</div>';
    }
    
    html += '</div>';
    container.innerHTML = html;
}

function findCategoryInTree(categories, targetId) {
    for (const cat of categories) {
        if (cat.id === targetId) return cat;
        if (cat.children) {
            const found = findCategoryInTree(cat.children, targetId);
            if (found) return found;
        }
    }
    return null;
}

function navigateToCategory(categoryId, categoryName) {
    currentRootId = categoryId;
    currentRootName = categoryName;
    loadPieData();
    loadCategoryTree();
}

function onRootClick() {
    // 点击根节点无操作，或者可以提示
    console.log('当前根节点:', currentRootName);
}

function goBack() {
    // 找到当前根节点的父节点
    // 简化处理：直接返回到根节点
    currentRootId = null;
    currentRootName = '';
    loadPieData();
    loadCategoryTree();
}

function formatDate(date) {
    return date.toISOString().split('T')[0];
}

async function loadOverview() {
    loadCategoryTree();
}
