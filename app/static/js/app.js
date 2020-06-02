document.addEventListener("DOMContentLoaded", function() {
	let carName = document.querySelector('#carName');
	let carModels =  document.querySelector('#carModel');
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
	getCars()

	carName.addEventListener('change', (e)=>{
		carModels.innerHTML = 'Выберите модель';
		async function getModels(){
			let carsUrl = `http://evgkarn.pythonanywhere.com/todo/api/v1.0/auto/${e.target.value}`;
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
		getModels()
	})

});
