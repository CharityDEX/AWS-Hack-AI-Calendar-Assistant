import { createSlice } from '@reduxjs/toolkit';

export const loadStatusSlice = createSlice({
  name: 'loadStatus',
  initialState: {
    load: false
  },
  reducers: {
    loadStatus: (state) => {
      state.load = true;
    },
  },
})

export const { loadStatus } = loadStatusSlice.actions;
export default loadStatusSlice.reducer;