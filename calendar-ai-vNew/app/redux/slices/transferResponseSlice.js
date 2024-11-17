import { createSlice } from '@reduxjs/toolkit';

export const transferResponseSlice = createSlice({
  name: 'transsferResponse',
  initialState: {
    response: [],
    oldData: {}
  },
  reducers: {
    sendSuggestedTimes: (state, action) => {
      state.response = action.payload;
    },
    storeOldData: (state, action) => {
      state.oldData = action.payload;
    }
  }
})

export const { sendSuggestedTimes, storeOldData } = transferResponseSlice.actions;
export default transferResponseSlice.reducer;