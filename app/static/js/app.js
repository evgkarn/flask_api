document.addEventListener("DOMContentLoaded", function() {
	let carName = document.querySelector('#carName');
	let carModels =  document.querySelector('#carModel');
	let carYear =  document.querySelector('#carYear');
	let cityIp =  document.querySelector('.cityIp');
	let searchForm = document.querySelector('.search-form');


	let url = String(window.location.href)
	
	// let url = `http://galiof.beget.tech/search?name=%D0%9C%D0%BE%D0%BB%D0%B4%D0%B8%D0%BD%D0%B3&mark_auto=BMW&model_auto=1%20%D1%81%D0%B5%D1%80%D0%B8%D1%8F`
	// console.log(decodeURIComponent('%D0%9C%D0%BE%D0%BB%D0%B4%D0%B8%D0%BD%D0%B3'))
	console.log(url.indexOf('&'))
	async function formInfo(){
		if (url.indexOf('?')>0){
			let arrUrl = url.split('?')
			arrUrl.shift()
			arrUrl = arrUrl.join('').split('&')
					
			for(let el of arrUrl){
				el = el.split('=')
				if(el[0] === 'name'){
					document.querySelector('#detailName').value = decodeURIComponent(el[1])
				}else if(el[0] === 'mark_auto'){
					await getCars()
					document.querySelector('#carName').value = decodeURIComponent(el[1])
				}else if(el[0] === 'model_auto'){
					await getModels()
	
					document.querySelector('#carModel').value = decodeURIComponent(el[1])
				}				
			}
		}else{
			 getCars()
		}
	}
	formInfo()
	// Получаем город пользователя
	async function getCity(){
		let response = await  fetch('http://free.ipwhois.io/json/?lang=ru', {
			method: 'GET'
		}).then((res)=>{
			return res.json()
		}).then(res => {
			cityIp.innerHTML = res.city
			console.log(res.city)

		} )
	
	}
	getCity()
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
		modelOption = [];
		modelOption.push( carsModel.model.map((carModel)=>{
			return `<option value='${carModel}'>${carModel} </option>`	
		}))
		for(let i = 0; i < modelOption.length; i++){
			carModels.innerHTML += modelOption[i];
		}
	}

	//Получение годов выпуска автомобилей

	async function getYears(){
		let carsUrl = `http://evgkarn.pythonanywhere.com/todo/api/v1.0/auto/${carName.value}/${carModels.value}`
		let response = await fetch(carsUrl, {
			method: 'GET'
		});
		carsYears = await response.json();
		yearOption = [];
		modelOption.push( carsModel.model.map((carModel)=>{
			return `<option value='${carModel}'>${carModel} </option>`	
		}))
		for(let i = 0; i < modelOption.length; i++){
			carYear.innerHTML += modelOption[i];
		}

	}
	carName.addEventListener('change', (e)=>{
		carModels.innerHTML = 'Выберите модель';

		getModels()
	})
	carModels.addEventListener('change', (e)=>{
		carYear.innerHTML = 'Выберите модель';

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
		adsInfoText[i].innerText = `${adsInfoText[i].textContent.substr(0,60)}`
	}
});

