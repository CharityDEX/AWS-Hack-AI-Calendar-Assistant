import { sendResponse } from '../api/sendResponse.js';
import { changeLoadStatus } from '../redux/slices/loadStatusSlice.js';
import { addDateTime } from '../redux/slices/meetingsSlice.js';
import { useDispatch } from 'react-redux';
import { useSelector } from 'react-redux';

const ChoiceRender = (props) => {
  const dispatch = useDispatch();
  const {date, startTime, endTime} = props.data;
  const oldData = useSelector(state => state.transferResponse.oldData);

  let dataToDispatch = {
    "date": date,
    "startTime": startTime,
    "endTime": endTime
  }

  const handleClick = async () => {
    dispatch(addDateTime(dataToDispatch));
    dispatch(changeLoadStatus());

    dataToDispatch = {
      ...dataToDispatch,
      ...oldData,
    }
    console.log(dataToDispatch);

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