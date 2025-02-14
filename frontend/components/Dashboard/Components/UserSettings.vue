<template>
  <div class="card flex md:flex-row w-full justify-end items-center py-4">
    <div
      class="flex flex-col lg:flex-row w-full md:w-[46rem] justify-center items-center bg-gray-100 dark:bg-gray-800 rounded-md p-4 shadow-lg gap-6"
    >
      <div class="text-right flex flex-col md:flex-row justify-center items-center gap-6">
        <p class="text-lg font-semibold text-center text-gray-700 dark:text-gray-300">{{userDisplayData.full_name}}</p>
        <div class="flex flex-col">
          <p class="text-sm text-center text-gray-500 dark:text-gray-400">Дата обновления:</p>
          <!-- <p class="text-sm text-center text-gray-500 dark:text-gray-400">{{formatRequestDate(request_date)}}</p> -->
        </div>
      </div>
	  
      <Button @click="reloadTable" label="Синхронизация" text class="p-button-danger bg-primary text-white h-10 hover:bg-secondaryDark min-w-[12rem]" />
	  <Button label="Экспорт в Excel" icon="pi pi-file-excel" class="p-button-success h-10 min-w-[12rem]"
              @click="exportToExcel" </Button>
    </div>
  </div>
</template>

<script setup>
// const { request_date } = useTableState();
const formatRequestDate = (isoDateString) => {
  // Parse the ISO date string into a Date object
  const date = new Date(isoDateString);

  // Extract the day, month, year, and time
  const day = String(date.getDate()).padStart(2, "0");
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const year = String(date.getFullYear()).slice(-2);

  // Extract hours and minutes
  const hours = String(date.getHours()).padStart(2, "0");
  const minutes = String(date.getMinutes()).padStart(2, "0");

  // Return the formatted date with the time from the ISO string
  return `${day}.${month}.${year} ${hours}:${minutes}`;
};
const { $listen } = useNuxtApp();
const { $event } = useNuxtApp();
function reloadTable() {
	useNuxtApp().$api
        .post(`api/admin/refresh/`)
        .then((response) => {
            let responseData = response.data;
            console.log("Profile responseData= ", responseData);
			$event('reloadTable');

        })
        .catch((err) => {
            if (err.response) {
                console.log(err.response.data)
            }
        });
}

function exportToExcel() {
	$event('exportToExcel');
}

let userDisplayData = ref({
	full_name: "",
	date: "",
});

const userData = await useAsyncData('userData', getuserData);

if (userData.data) {
    if (userData.data.value) {
		setData(userData.data.value);
        
    }
}
function setData(data) {
	if (data) {	
		console.log("userData data= ", data);
		userDisplayData.value.full_name = data.full_name;
	}
}

async function getuserData() {
    let responseData
    await useNuxtApp().$api
        .get(`api/auth/me/`)
        .then((response) => {
            responseData = response.data;
            console.log("Profile responseData= ", responseData);
        })
        .catch((err) => {
            if (err.response) {
                // //console.log(err.response.data)
            }
        });
    return responseData
}


</script>
