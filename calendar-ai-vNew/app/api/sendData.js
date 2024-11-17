import axiosInstance from './axiosInstance';

const sendData = async (data) => {
  const response = await axiosInstance.post('/items/', data);
  return response.data;
}

export default sendData;