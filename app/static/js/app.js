document.addEventListener("DOMContentLoaded", function() {
	
	let carName = document.querySelector('#carName');
	let carModels =  document.querySelector('#carModel');
	let carYear =  document.querySelector('#carYear');
	let cityIp =  document.querySelector('.cityIp');
	let searchForm = document.querySelector('.search-form');
	let carImage = document.querySelector('.search-form img')

	let url = String(window.location.href)
	
	
	if(carName){


		console.log(url.indexOf('&'))
		async function formInfo(){
			if (url.indexOf('search?')>0){
				let arrUrl = url.split('?')
				arrUrl.shift()
				arrUrl = arrUrl.join('').split('&')
						
				for(let el of arrUrl){
					el = el.split('=')
					if(el[0] === 'name'){
						document.querySelector('#detailName').value = decodeURIComponent(el[1])
						await getCars()
					}else if(el[0] === 'mark_auto'){
						await getCars()
						document.querySelector('#carName').value = decodeURIComponent(el[1])
					}else if(el[0] === 'model_auto'){
						await getModels()
		
						document.querySelector('#carModel').value = decodeURIComponent(el[1])
					}else if(el[0] === 'year_auto'){
						await getYears()
		
						document.querySelector('#carYear').value = decodeURIComponent(el[1])
					}					
				}
			}else{
				 getCars()
			}
		}
		formInfo()

		 // Получаем список автомобилей
	async function getCars(){
		let carsUrl = 'https://azato.ru/todo/api/v1.0/auto';
		let response = await fetch(carsUrl, {
			method: 'GET'
		});
		cars = await response.json();
		carsOption = [];
		carsOption.push( cars.auto.map((carModel)=>{
			return `<option value='${carModel}'>${carModel} </option>`	
		}))
		console.log(carsOption)
		for(let i = 0; i < carsOption.length; i++){
			carName.innerHTML += carsOption[i];
		}
	}
	// getCars()

	// Получаем список моделей
	async function getModels(){
		console.log(carName.value)
		let carsUrl = `https://azato.ru/todo/api/v1.0/auto/${carName.value}`;
		let response = await fetch(carsUrl, {
			method: 'GET'
		});
		carsModel = await response.json();
		modelOption = [`<option value='all'>Все</option>`];
		carModels.remove(0);
		modelOption.push( carsModel.model.map((carModel)=>{
			return `<option value='${carModel}'>${carModel} </option>`	
		}))
		for(let i = 0; i < modelOption.length; i++){
			carModels.innerHTML += modelOption[i];
		}
	}

	//Получение годов выпуска автомобилей

	async function getYears(){
		let carYear =  document.querySelector('#carYear');
		let carsUrl = `https://azato.ru/todo/api/v1.0/auto/${carName.value}/${carModels.value}`
		let response = await fetch(carsUrl, {
			method: 'GET'
		});
		carsYears = await response.json();
		yearOption = [`<option value='all'>Все</option>`];
		var length = carYear.options.length;
		for (i = length-1; i >= 0; i--) {
  		carYear.options[i] = null;
			}
		yearOption.push( carsYears.year.map((carYear)=>{
			return `<option value='${carYear}'>${carYear} </option>`	
		}))
		for(let i = 0; i < yearOption.length; i++){
			carYear.innerHTML += yearOption[i];
		}

	}
	async function getAll(){
		await getModels()
		await getYears()
	}
	carName.addEventListener('change', (e)=>{
		carModels.innerHTML = `<option>Загрузка моделей...</option>`;
		getAll()
	})
	carModels.addEventListener('change', (e)=>{
		carYear.innerHTML = `<option>Загрузка годов...</option>`;

		getYears()
	})
	//Поиск запчасти
	searchForm.addEventListener('submit', (e)=>{
		e.preventDefault();
		let name = searchForm.querySelector('#detailName').value
		let markAuto = searchForm.querySelector('#carName').value
		let modelAuto = searchForm.querySelector('#carModel').value
		let carYear = searchForm.querySelector('#carYear').value
		window.location = `https://azato.ru/search?${name.length > 1 ? 'name=' + name : ''}
		${markAuto.length > 1 ? '&mark_auto=' + markAuto : ''}
		${modelAuto.length > 1 ? '&model_auto=' + modelAuto : ''}
		${carYear.length > 1 ? '&year_auto=' + carYear : ''}`
	})

	let adsInfoText = document.querySelectorAll('.ads-info p');


	for(let i = 0; i< adsInfoText.length; i++){
		adsInfoText[i].innerText.length > 40 ? adsInfoText[i].innerText = `${adsInfoText[i].textContent.substr(0,60)}...` : adsInfoText[i].innerText = `${adsInfoText[i].textContent.substr(0,60)}`
	}
	}

	// Получаем город пользователя
	// async function getCity(){
	// 	let response = await  fetch('http://free.ipwhois.io/json/?lang=ru', {
	// 		method: 'GET'
	// 	}).then((res)=>{
	// 		return res.json()
	// 	}).then(res => {
	// 		cityIp.innerHTML = res.city
	// 		console.log(res.city)

	// 	} )
	
	// }
	// getCity()
	

		//Заказ консультации

		let leftform = document.querySelector('.right-form-block'),
		contactButton = document.querySelector('.send-message'),
		formClose = document.querySelector('.form-close')
		messageForm = document.querySelector('.top-form');
if(contactButton){
	contactButton.addEventListener('click', function(e){
		e.preventDefault();
		leftform.classList.toggle('show-form');
	});
	formClose.addEventListener('click', function(e){
		e.preventDefault();
		leftform.classList.toggle('show-form');
	});
	messageForm.addEventListener('submit',(e)=>{
		e.preventDefault();
		console.log('Отправили!')
		putMessage();
	})
}


		// Отправка заявки

		async function putMessage(){

			const dateData = new FormData();
			dateData.append('shop_id', document.getElementById('shop_id').value)
			dateData.append('ad_id', document.getElementById('ad_id').value)
			dateData.append('name', document.querySelector('.top-form #name').value)
			dateData.append('phone', document.querySelector('.top-form #phone').value)
			dateData.append('email', document.querySelector('.top-form #email').value)
			dateData.append('text', document.querySelector('.top-form #text').value)

			
			let response = await fetch('https://azato.ru/todo/api/v1.0/order', {
				method: 'post',
				body: dateData
			}).then((res) =>{
				messageForm.innerHTML = '<h2>Ваш запрос отправлен</h2>'
				console.log(res)
			})
	
		}

	// Получение телефонов по клику

	let phones = document.querySelectorAll('.results-ads-more button')
		console.log(phones)
	if(phones){
		for(let i=0; i<phones.length; i++){
			phones[i].addEventListener('click',(e)=>{
				e.preventDefault();
				const numb = phones[i].value;

				phones[i].innerText = numb;
				console.log(phones[i].value)
			})
		}

	}

	if(searchForm){
		carImage.addEventListener('click', ()=>{
			carImage.classList.add('animation-car')
		})
	}
});

