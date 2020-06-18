document.addEventListener("DOMContentLoaded", function() {
	let carName = document.querySelector('#carName');
	let carModels =  document.querySelector('#carModel');
	let cityIp =  document.querySelector('.cityIp');
	let searchForm = document.querySelector('.search-form');


	let url = String(window.location.href)
	console.log(url.indexOf('&'))
	async function formInfo(){
		if (url.indexOf('&')>0){
			let arrUrl = url.split('?')
			arrUrl.shift()
			arrUrl = arrUrl.join('').split('&')
					
			for(let el of arrUrl){
				el = el.split('=')
				if(el[0] === 'name'){
					document.querySelector('#detailName').value = el[1]
				}else if(el[0] === 'mark_auto'){
				console.log('mark auto')
					await getCars()
					document.querySelector('#carName').value = el[1]
				}else if(el[0] === 'model_auto'){
                     console.log('model auto')
					await getModels()
					document.querySelector('#carModel').value = el[1]
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
		let carsUrl = 'http://evgkarn.pythonanywhere.com/todo/api/v1.0/auto';
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
		let carsUrl = `http://evgkarn.pythonanywhere.com/todo/api/v1.0/auto/${carName.value}`;
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
	carName.addEventListener('change', (e)=>{
		carModels.innerHTML = 'Выберите модель';

		getModels()
	})

	//Поиск запчасти
	searchForm.addEventListener('submit', (e)=>{
		e.preventDefault();
		let name = searchForm.querySelector('#detailName').value
		let markAuto = searchForm.querySelector('#carName').value
		let modelAuto = searchForm.querySelector('#carModel').value
		window.location = `http://evgkarn.pythonanywhere.com/search?${name.length > 1 ? 'name=' + name : ''}
		${markAuto.length > 1 ? '&mark_auto=' + markAuto : ''}
		${modelAuto.length > 1 ? '&model_auto=' + modelAuto : ''}`
	})

	let adsInfoText = document.querySelectorAll('.ads-info p');

	for(let i = 0; i< adsInfoText.length; i++){
		console.log(adsInfoText[i])
		adsInfoText[i].innerText = `${adsInfoText[i].textContent.substr(0,60)}`
	}
});

