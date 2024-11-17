import { sendResponse } from '../api/sendResponse.js';
import { changeLoadStatus } from '../redux/slices/loadStatusSlice.js';
import { addDateTime } from '../redux/slices/meetingsSlice.js';
import { useDispatch } from 'react-redux';

const ChoiceRender = (props) => {
  const dispatch = useDispatch();
  const {date, startTime, endTime} = props.data;
  
  const dataToDispatch = {
    "date": date,
    "startTime": startTime,
    "endTime": endTime
  }

  const handleClick = async () => {
    console.log(dataToDispatch);
    dispatch(addDateTime(dataToDispatch));
    dispatch(changeLoadStatus());
    try {
      const response = await sendResponse(dataToDispatch);
      console.log(response);
    } catch (error) {
      console.log(error);
    }
  }

  console.log(date);

  return (
    <div className="choice-card">
      <p className="date-text">Date: {date}</p>
      <p className="time-text">Time: {startTime} - {endTime}</p>
      <button onClick={handleClick}>Choose Time</button>
    </div>
  )
}

export default ChoiceRender;