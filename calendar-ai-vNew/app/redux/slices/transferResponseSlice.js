import { createSlice } from '@reduxjs/toolkit';

export const transferResponseSlice = createSlice({
  name: 'transsferResponse',
  initialState: {
    response: []
  },
  reducers: {
    sendSuggestedTimes: (state, action) => {
      state.response = action.payload;
    }
  }
})

export const { sendSuggestedTimes } = transferResponseSlice.actions;
export default transferResponseSlice.reducer;