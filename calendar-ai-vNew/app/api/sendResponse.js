import axiosInstance from './axiosInstance';

const sendResponse = async (data) => {
  const response = await axiosInstance.post('/data/', data);
  return response.data;
}

export default sendResponse;