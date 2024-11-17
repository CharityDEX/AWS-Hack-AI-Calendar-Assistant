import { createSlice } from '@reduxjs/toolkit';

export const loadStatusSlice = createSlice({
  name: 'loadStatus',
  initialState: {
    load: false
  },
  reducers: {
    changeLoadStatus: (state) => {
      state.load = true;
    },
  },
})

export const { changeLoadStatus } = loadStatusSlice.actions;
export default loadStatusSlice.reducer;