document.addEventListener('DOMContentLoaded', () => {
    const burger = document.getElementById('burgerBtn');
    const navList = document.getElementById('navList');
    if (burger) {
        burger.addEventListener('click', () => {
            navList.classList.toggle('active');
        });
    }

    const categories = document.querySelectorAll('.category-card');
    const productsContainer = document.getElementById('productsContainer');
    const mockProducts = {
        pumps: [
            { name: 'Центробежный насос XH-150', desc: 'Производительность до 500 м³/ч, взрывозащищенное исполнение' },
            { name: 'Насос шестеренчатый НШ-100', desc: 'Для перекачки вязких нефтепродуктов' },
            { name: 'Погружной насос ЭЦН', desc: 'Для добычи пластовой жидкости' }
        ],
        valves: [
            { name: 'Задвижка клиновая 30с941нж', desc: 'Ду 300, Ру 16, с эл. приводом' },
            { name: 'Клапан обратный поворотный', desc: 'Dy 200, корпус из стали' }
        ],
        compressors: [
            { name: 'Винтовой компрессор ВК-37', desc: 'Производительность 6,2 м³/мин' }
        ],
        heat: [
            { name: 'Пластинчатый теплообменник M6', desc: 'Тепловая мощность 500 кВт' }
        ],
        filters: [
            { name: 'Фильтр сетчатый ФС', desc: 'Номинальное давление 1,6 МПа' }
        ],
        automation: [
            { name: 'Контроллер S7-1200', desc: 'Система автоматизации технологических процессов' }
        ]
    };
    function renderProducts(catKey) {
        let products = mockProducts[catKey] || mockProducts.pumps;
        productsContainer.innerHTML = '';
        products.forEach(prod => {
            const productDiv = document.createElement('div');
            productDiv.className = 'product-item';
            productDiv.innerHTML = `
                <div class="product-img placeholder-img"></div>
                <div class="product-info"><h4>${prod.name}</h4><p>${prod.desc}</p></div>
            `;
            productsContainer.appendChild(productDiv);
        });
    }
    if (categories.length && productsContainer) {
        categories.forEach(cat => {
            cat.addEventListener('click', () => {
                categories.forEach(c => c.classList.remove('active'));
                cat.classList.add('active');
                const category = cat.getAttribute('data-category');
                renderProducts(category);
            });
        });
        renderProducts('pumps');
    }

    const track = document.getElementById('carouselTrack');
    const prevBtn = document.getElementById('prevBtn');
    const nextBtn = document.getElementById('nextBtn');
    const dotsContainer = document.getElementById('carouselDots');
    if (track) {
        let slides = Array.from(document.querySelectorAll('.partner-card'));
        let currentIdx = 0;
        let autoInterval;
        function getSlidesPerView() {
            return window.innerWidth <= 768 ? 1 : 3;
        }
        function updateCarousel() {
            const perView = getSlidesPerView();
            const maxIndex = Math.max(0, slides.length - perView);
            if (currentIdx > maxIndex) currentIdx = maxIndex;
            const offset = -(currentIdx * (100 / perView));
            track.style.transform = `translateX(${offset}%)`;
            updateDots();
        }
        function updateDots() {
            if (!dotsContainer) return;
            const perView = getSlidesPerView();
            const totalDots = Math.ceil(slides.length / perView);
            dotsContainer.innerHTML = '';
            for (let i = 0; i < totalDots; i++) {
                const dot = document.createElement('div');
                dot.classList.add('dot');
                if (i === currentIdx) dot.classList.add('active');
                dot.addEventListener('click', () => {
                    currentIdx = i;
                    updateCarousel();
                    resetAuto();
                });
                dotsContainer.appendChild(dot);
            }
        }
        function nextSlide() {
            const perView = getSlidesPerView();
            const max = Math.ceil(slides.length / perView) - 1;
            if (currentIdx < max) currentIdx++;
            else currentIdx = 0;
            updateCarousel();
        }
        function prevSlide() {
            const perView = getSlidesPerView();
            const max = Math.ceil(slides.length / perView) - 1;
            if (currentIdx > 0) currentIdx--;
            else currentIdx = max;
            updateCarousel();
        }
        function resetAuto() {
            if (autoInterval) clearInterval(autoInterval);
            autoInterval = setInterval(() => nextSlide(), 4000);
        }
        if (prevBtn) prevBtn.addEventListener('click', () => { prevSlide(); resetAuto(); });
        if (nextBtn) nextBtn.addEventListener('click', () => { nextSlide(); resetAuto(); });
        window.addEventListener('resize', () => {
            updateCarousel();
            resetAuto();
        });
        updateCarousel();
        resetAuto();
    }
});