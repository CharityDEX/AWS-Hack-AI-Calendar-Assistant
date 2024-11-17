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

  const handleClick = () => {
    console.log(dataToDispatch);
    dispatch(addDateTime(dataToDispatch));
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